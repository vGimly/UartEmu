import logging
from dataclasses import dataclass


log = logging.getLogger("uart.protocol")


START_STOP = 0x7E
ESCAPE = 0x7D
ESCAPE_START = 0x5E
ESCAPE_ESCAPE = 0x5D

ERROR_TIMEOUT = 0x80
ERROR_SHORT = 0x81
ERROR_CRC = 0x82
ERROR_ESCAPE = 0x83
ERROR_GARBAGE = 0x84

CRC16_INIT = 0xFFFF


@dataclass
class Frame:
    cmd: int
    payload: bytes
    crc: int


@dataclass
class ProtocolError:
    code: int
    detail: str = ""


class FrameParser:
    """
    Streaming parser:

        7E [escaped(cmd + payload + crc16)] 7E

    CRC is calculated over unescaped cmd + payload.
    The last two unescaped bytes are the received CRC.
    """

    def __init__(self, timeout=1.0):
        self.timeout = timeout
        self.reset()

    def reset(self):
        self.in_frame = False
        self.in_garbage = False
        self.escaped = False

        self.data = bytearray()
        self.tail = bytearray()

        self.crc = CRC16_INIT

    def feed(self, data):
        """
        Feed arbitrary chunks of a TCP stream.

        Returns a list of Frame / ProtocolError objects.
        """
        result = []

        for byte in data:
            event = self.feed_byte(byte)

            if event is not None:
                result.append(event)

        return result

    def feed_byte(self, byte):
        # ------------------------------------------------------------
        # IDLE
        # ------------------------------------------------------------

        if not self.in_frame and not self.in_garbage:
            if byte == START_STOP:
                self.start_frame()
                log.debug("START")
                return None

            self.in_garbage = True
            log.debug("GARBAGE start: %02x", byte)
            return None

        # ------------------------------------------------------------
        # GARBAGE
        # ------------------------------------------------------------

        if self.in_garbage:
            if byte != START_STOP:
                return None

            # This 7E terminates garbage and simultaneously starts
            # the next frame.

            log.warning("GARBAGE terminated by START")

            self.start_frame()

            return ProtocolError(
                ERROR_GARBAGE,
                "garbage before start",
            )

        # ------------------------------------------------------------
        # ESCAPE
        # ------------------------------------------------------------

        if self.escaped:
            if byte == ESCAPE_START:
                byte = START_STOP

            elif byte == ESCAPE_ESCAPE:
                byte = ESCAPE

            else:
                log.warning(
                    "invalid ESCAPE sequence: 7d %02x",
                    byte,
                )

                self.reset()

                return ProtocolError(
                    ERROR_ESCAPE,
                    "invalid escape 0x%02x" % byte,
                )

            self.escaped = False

            return self.process_data_byte(byte)

        # ------------------------------------------------------------
        # FRAME
        # ------------------------------------------------------------

        if byte == ESCAPE:
            self.escaped = True
            return None

        if byte == START_STOP:
            return self.finish_frame()

        return self.process_data_byte(byte)

    def start_frame(self):
        self.in_frame = True
        self.in_garbage = False
        self.escaped = False

        self.data.clear()
        self.tail.clear()

        self.crc = CRC16_INIT

    def process_data_byte(self, byte):
        """
        Keep the last two unescaped bytes in tail.

        Everything before tail is cmd + payload and is included
        in the running CRC.
        """

        self.tail.append(byte)

        if len(self.tail) > 2:
            data_byte = self.tail.pop(0)

            self.data.append(data_byte)
            self.crc = update_crc(data_byte, self.crc)

        return None

    def finish_frame(self):
        """
        STOP received.
        """

        # Normally an escaped state is handled before STOP, but keep
        # this check here for completeness.

        if self.escaped:
            log.warning("frame ended in ESCAPE state")

            self.reset()

            return ProtocolError(
                ERROR_ESCAPE,
                "frame ended after escape",
            )

        # Fewer than two bytes means there cannot be a CRC.

        if len(self.tail) < 2:
            log.warning(
                "SHORT frame: %d byte(s)",
                len(self.data) + len(self.tail),
            )

            self.reset()

            return ProtocolError(
                ERROR_SHORT,
                "frame too short",
            )

        received_crc = (self.tail[0] << 8) | self.tail[1]

        calculated_crc = self.crc

        if received_crc != calculated_crc:
            log.warning(
                "CRC error: received=0x%04x calculated=0x%04x",
                received_crc,
                calculated_crc,
            )

            self.reset()

            return ProtocolError(
                ERROR_CRC,
                "received=0x%04x calculated=0x%04x" % (received_crc, calculated_crc),
            )

        # At least CMD must be present.

        if not self.data:
            log.warning("SHORT frame: no CMD")

            self.reset()

            return ProtocolError(
                ERROR_SHORT,
                "no command",
            )

        cmd = self.data[0]
        payload = bytes(self.data[1:])

        frame = Frame(
            cmd=cmd,
            payload=payload,
            crc=received_crc,
        )

        log.info(
            "FRAME cmd=0x%02x payload=%s crc=0x%04x",
            cmd,
            payload.hex(" "),
            received_crc,
        )

        self.reset()

        return frame

    def timeout_expired(self):
        """
        Called by UARTServer when the receive timeout expires.

        No error is generated while IDLE.
        """

        if self.in_frame:
            log.warning("FRAME timeout")

            self.reset()

            return ProtocolError(
                ERROR_TIMEOUT,
                "frame receive timeout",
            )

        if self.in_garbage:
            log.warning("GARBAGE timeout")

            self.reset()

            return ProtocolError(
                ERROR_GARBAGE,
                "garbage receive timeout",
            )

        return None

def calc_crc(cmd, payload):
    crc = CRC16_INIT

    crc = update_crc(cmd, crc)

    for byte in payload:
        crc = update_crc(byte, crc)

    return crc

def encode_frame(cmd, payload):
    """
    Build:

        7E [escaped(cmd + payload + crc16)] 7E
    """

    body = bytearray()

    body.append(cmd)
    body.extend(payload)

    crc = calc_crc(cmd, payload)

    body.append((crc >> 8) & 0xFF)
    body.append(crc & 0xFF)

    frame = bytes((START_STOP,)) + escape(body) + bytes((START_STOP,))

    log.info(
        "ENCODE cmd=0x%02x payload=%s crc=0x%04x",
        cmd,
        payload.hex(" "),
        crc,
    )

    return frame


def encode_error(error_code):
    """
    Build:

        7E FF error_code crc16 7E
    """

    log.warning(
        "ENCODE ERROR code=0x%02x",
        error_code,
    )

    return encode_frame(
        0xFF,
        bytes((error_code,)),
    )


def escape(data):
    result = bytearray()

    for byte in data:
        if byte == START_STOP:
            result.extend((ESCAPE, ESCAPE_START))

        elif byte == ESCAPE:
            result.extend((ESCAPE, ESCAPE_ESCAPE))

        else:
            result.append(byte)

    return bytes(result)


def update_crc(byte, crc):
    """
    CRC-16/CCITT

        polynomial = 0x1021
        initial    = 0xFFFF
    """

    crc ^= byte << 8

    for _ in range(8):
        if crc & 0x8000:
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF
        else:
            crc = (crc << 1) & 0xFFFF

    return crc

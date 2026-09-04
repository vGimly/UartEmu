from protocol import (
    ProtocolError,
    ERROR_SHORT,
    ERROR_CRC,
    ERROR_GARBAGE,
    START_STOP,
    FrameParser,
    encode_frame,
)


def parse(data):
    parser = FrameParser()
    events = parser.feed(data)
    assert len(events) == 1
    return events[0]


def test_empty_frame():
    event = parse(bytes([
        START_STOP,
        START_STOP,
    ]))

    assert isinstance(event, ProtocolError)
    assert event.code == ERROR_SHORT


def test_one_byte_frame():
    event = parse(bytes([
        START_STOP,
        0x01,
        START_STOP,
    ]))

    assert isinstance(event, ProtocolError)
    assert event.code == ERROR_SHORT


def test_bad_crc():
    frame = bytearray(
        encode_frame(0x01, b"hello")
    )

    # Change one byte of the CRC.
    frame[-2] ^= 0x01

    event = parse(bytes(frame))

    assert isinstance(event, ProtocolError)
    assert event.code == ERROR_CRC


def test_garbage():
    parser = FrameParser()

    events = parser.feed(bytes([
        0x01,
        0x02,
        0x03,
        START_STOP,
    ]))

    assert len(events) == 1
    assert isinstance(events[0], ProtocolError)
    assert events[0].code == ERROR_GARBAGE

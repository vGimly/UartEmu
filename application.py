from state import DeviceState
import datetime

state = DeviceState()


def command(client, cmd, payload):
    if cmd == 0x01:
        return b"OK=" + payload

    if cmd == 0x02:
        return register_read_write(cmd, payload)

    if cmd == 0x03:
        return datetime.datetime.now().strftime("%Y%m%d %H%M%S").encode("ascii")

    return None


def register_read_write(id, payload):
    if not payload:
        return None

    operation = payload[0]
    rest = payload[1:]

    # Skip up to five optional zero bytes.
    zeros = 0
    while zeros < 5 and rest[:1] == b"\x00":
        rest = rest[1:]
        zeros += 1

    if operation == 0x01:
        value = state.read(id)
        return str(value).encode("ascii")

    if operation == 0x02:
        try:
            value = int(rest.decode("ascii"), 10)
        except (UnicodeDecodeError, ValueError):
            return None

        state.write(id, value)
        return b""

    return None

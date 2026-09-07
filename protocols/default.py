"""
device: generic
version: 1.0.0
description: Протокол по умолчанию — эхо, чтение/запись регистров, время устройства.
"""

import datetime

from state import DeviceState

state = DeviceState()


def command(client, cmd, payload):
    if cmd == 0x01: # echo
        return b"OK=" + payload

    if cmd == 0x02: # read-write register
        return register_read_write(cmd, payload)

    if cmd == 0x03: # date-time
        return datetime.datetime.now().strftime("%Y%m%d %H%M%S").encode("ascii")

    return None


def register_read_write(id, payload):
    if not payload:
        return b"-2"

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
            return b"-1"

        state.write(id, value)
        return b""

    return b"-3"

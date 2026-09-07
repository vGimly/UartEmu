"""
device: generic
version: 1.0.0
description: Default echo, register, and date-time protocol.
"""

import datetime

from state import DeviceState

state = DeviceState()


def command(client, cmd, payload):
    if cmd == 0x01:
        return b"OK=" + payload

    if cmd == 0x02:
        return register_read_write(client, cmd, payload)

    if cmd == 0x03:
        return datetime.datetime.now().strftime("%Y%m%d %H%M%S").encode("ascii")

    return None


def register_read_write(client, address, payload):
    if not payload:
        return b"-2"

    operation = payload[0]
    rest = payload[1:]

    zeros = 0
    while zeros < 5 and rest[:1] == b"\x00":
        rest = rest[1:]
        zeros += 1

    device_id = client.get("device_id")
    if device_id is None:
        return b"-4"

    if operation == 0x01:
        value = state.read(device_id, address)
        return str(value).encode("ascii")

    if operation == 0x02:
        try:
            value = int(rest.decode("ascii"), 10)
        except (UnicodeDecodeError, ValueError):
            return b"-1"

        state.write(device_id, address, value)
        return b""

    return b"-3"

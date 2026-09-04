import asyncio

import pytest

from protocol import ERROR_TIMEOUT, encode_frame
from lib.uart import connect_uart, read_event


@pytest.mark.asyncio
async def test_frame_timeout():
    reader, writer = await connect_uart()

    try:
        writer.write(b"\x7e\x01hello")
        await writer.drain()

        event = await read_event(reader, timeout=3.0)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_TIMEOUT])

    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_frame_timeout_resets_parser():
    reader, writer = await connect_uart()

    try:
        writer.write(b"\x7e\x01broken")
        await writer.drain()

        event = await read_event(reader, timeout=3.0)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_TIMEOUT])

        writer.write(encode_frame(0x01, b"after-timeout"))
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0x01
        assert event.payload == b"OK=after-timeout"

    finally:
        writer.close()
        await writer.wait_closed()

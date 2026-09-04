import pytest

from protocol import ERROR_GARBAGE, encode_frame
from lib.uart import connect_uart, read_event


@pytest.mark.asyncio
async def test_garbage():
    reader, writer = await connect_uart()

    try:
        writer.write(b"\x11\x22\x33\x44")
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_GARBAGE])

    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_garbage_resets_parser():
    reader, writer = await connect_uart()

    try:
        writer.write(b"\x11\x22\x33")
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_GARBAGE])

        writer.write(encode_frame(0x01, b"after-garbage"))
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0x01
        assert event.payload == b"OK=after-garbage"

    finally:
        writer.close()
        await writer.wait_closed()

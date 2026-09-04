import pytest

from protocol import encode_frame
from lib.uart import connect_uart, read_event


@pytest.mark.asyncio
async def test_split_frame():
    reader, writer = await connect_uart()

    try:
        frame = encode_frame(0x01, b"split")

        writer.write(frame[:3])
        await writer.drain()

        writer.write(frame[3:])
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0x01
        assert event.payload == b"OK=split"

    finally:
        writer.close()
        await writer.wait_closed()

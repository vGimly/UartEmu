import pytest

from protocol import encode_frame
from lib.uart import connect_uart, read_event


@pytest.mark.asyncio
async def test_disconnect_during_frame():
    reader, writer = await connect_uart()

    writer.write(b"\x7e\x01hello")
    await writer.drain()

    writer.close()
    await writer.wait_closed()

    # A new client must still be served.
    reader, writer = await connect_uart()

    try:
        writer.write(encode_frame(0x01, b"after-disconnect"))
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0x01
        assert event.payload == b"OK=after-disconnect"

    finally:
        writer.close()
        await writer.wait_closed()

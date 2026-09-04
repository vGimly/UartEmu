import re

import pytest

from protocol import encode_frame
from lib.uart import connect_uart, read_event


@pytest.mark.asyncio
async def test_datetime():
    reader, writer = await connect_uart()

    try:
        writer.write(encode_frame(0x03, b""))
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0x03
        assert re.fullmatch(
            rb"\d{8} \d{6}",
            event.payload,
        )

    finally:
        writer.close()
        await writer.wait_closed()

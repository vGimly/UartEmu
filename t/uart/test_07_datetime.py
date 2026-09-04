import re

import pytest

from protocol import encode_frame
from lib.uart import connect_uart, uart_command


@pytest.mark.asyncio
async def test_datetime():
    reader, writer = await connect_uart()

    try:
        payload = await uart_command(
            reader,
            writer,
            0x03,
        )

        assert re.fullmatch(
            rb"\d{8} \d{6}",
            payload,
        )

    finally:
        writer.close()
        await writer.wait_closed()

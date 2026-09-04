import pytest
import random

from lib.uart import connect_uart, uart_get, uart_set


@pytest.mark.asyncio
async def test_param_02_set_get():
    reader, writer = await connect_uart()

    try:
        value = random.randint(-512, 511)

        await uart_set(
            reader,
            writer,
            0x02,
            value,
        )

        got = await uart_get(
            reader,
            writer,
            0x02,
        )

        assert got == str(value).encode("ascii")

    finally:
        writer.close()
        await writer.wait_closed()

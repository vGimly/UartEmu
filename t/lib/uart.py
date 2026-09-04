# t/lib/common.py

import asyncio

from protocol import FrameParser


UART_HOST = "10.9.0.1"
UART_PORT = 7000

API_URL = "http://127.0.0.1:8000"


async def connect_uart():
    return await asyncio.open_connection(
        UART_HOST,
        UART_PORT,
    )


async def read_event(reader, timeout=2.0):
    parser = FrameParser(timeout=timeout)

    while True:
        data = await asyncio.wait_for(
            reader.read(4096),
            timeout=timeout,
        )

        if not data:
            raise AssertionError(
                "connection closed while waiting for frame"
            )

        events = parser.feed(data)

        if events:
            return events[0]

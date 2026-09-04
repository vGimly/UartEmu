# t/lib/common.py

import asyncio

from protocol import FrameParser, encode_frame


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
            raise AssertionError("connection closed while waiting for frame")

        events = parser.feed(data)

        if events:
            return events[0]


async def uart_command(reader, writer, cmd, payload=b""):
    writer.write(encode_frame(cmd, payload))
    await writer.drain()

    event = await read_event(reader)

    assert event.cmd == cmd

    return event.payload


async def uart_get(reader, writer, cmd):
    return await uart_command(
        reader,
        writer,
        cmd,
        b"\x01",
    )


async def uart_set(reader, writer, cmd, value):
    return await uart_command(
        reader,
        writer,
        cmd,
        b"\x02" + str(value).encode("ascii"),
    )

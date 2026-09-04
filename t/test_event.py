import asyncio

import pytest

from protocol import FrameParser
from lib.api import request
from lib.uart import connect_uart


async def read_frame(reader, timeout=2.0):
    parser = FrameParser()

    while True:
        data = await asyncio.wait_for(
            reader.read(4096),
            timeout=timeout,
        )

        assert data

        events = parser.feed(data)

        if events:
            assert len(events) == 1
            return events[0]


@pytest.mark.asyncio
async def test_api_event():
    reader, writer = await connect_uart()

    try:
        status, data = request(
            "POST",
            "/api/event",
            {
                "cmd": 0x42,
                "payload": "0102037d7e",
            },
        )

        assert status == 200
        assert data["cmd"] == 0x42
        assert data["payload"] == "0102037d7e"
        assert data["clients"] == 1

        event = await read_frame(reader)

        assert event.cmd == 0x42
        assert event.payload == bytes.fromhex("0102037d7e")

    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_api_event_multiple_clients():
    clients = [
        await connect_uart(),
        await connect_uart(),
        await connect_uart(),
    ]

    try:
        status, data = request(
            "POST",
            "/api/event",
            {
                "cmd": 0x42,
                "payload": "0102037d7e",
            },
        )

        assert status == 200
        assert data["cmd"] == 0x42
        assert data["payload"] == "0102037d7e"
        assert data["clients"] == 3

        events = await asyncio.gather(
            *(read_frame(reader) for reader, writer in clients)
        )

        for event in events:
            assert event.cmd == 0x42
            assert event.payload == bytes.fromhex("0102037d7e")

    finally:
        for reader, writer in clients:
            writer.close()

        await asyncio.gather(*(writer.wait_closed() for reader, writer in clients))

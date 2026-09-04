import pytest

from protocol import (
    ERROR_SHORT,
    ERROR_ESCAPE,
    ERROR_CRC,
    START_STOP,
    ESCAPE,
    encode_frame,
)

from lib.uart import connect_uart, read_event


@pytest.mark.asyncio
async def test_short_frame():
    reader, writer = await connect_uart()

    try:
        writer.write(
            bytes(
                [
                    START_STOP,
                    0x01,
                    START_STOP,
                ]
            )
        )
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_SHORT])

    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_bad_escape():
    reader, writer = await connect_uart()

    try:
        writer.write(
            bytes(
                [
                    START_STOP,
                    0x01,
                    ESCAPE,
                    0x83,
                ]
            )
        )
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_ESCAPE])

    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_bad_crc():
    reader, writer = await connect_uart()

    try:
        frame = bytearray(encode_frame(0x01, b"hello"))

        frame[-2] ^= 0x01

        writer.write(frame)
        await writer.drain()

        event = await read_event(reader)

        assert event.cmd == 0xFF
        assert event.payload == bytes([ERROR_CRC])

    finally:
        writer.close()
        await writer.wait_closed()

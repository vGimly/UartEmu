import pytest

from protocol import (
    Frame,
    ProtocolError,
    ERROR_ESCAPE,
    encode_frame,
    FrameParser,
)


def parse(data):
    parser = FrameParser()
    events = parser.feed(data)
    assert len(events) == 1
    return events[0]


def test_escape_start_stop():
    frame = parse(encode_frame(0x01, bytes([0x7E])))

    assert isinstance(frame, Frame)
    assert frame.cmd == 0x01
    assert frame.payload == bytes([0x7E])


def test_escape_escape():
    frame = parse(encode_frame(0x01, bytes([0x7D])))

    assert isinstance(frame, Frame)
    assert frame.cmd == 0x01
    assert frame.payload == bytes([0x7D])


def test_invalid_escape():
    frame = parse(bytes([
        0x7E,
        0x01,
        0x7D,
        0x83,
    ]))

    assert isinstance(frame, ProtocolError)
    assert frame.code == ERROR_ESCAPE

from protocol import Frame, FrameParser, encode_frame


def test_command_escape():
    parser = FrameParser()

    frame = encode_frame(0x7E, b"hello")

    assert frame.startswith(b"\x7e\x7d\x5e")

    events = parser.feed(frame)

    assert len(events) == 1
    assert isinstance(events[0], Frame)
    assert events[0].cmd == 0x7E
    assert events[0].payload == b"hello"


def test_command_escape_7d():
    parser = FrameParser()

    frame = encode_frame(0x7D, b"hello")

    assert frame.startswith(b"\x7e\x7d\x5d")

    events = parser.feed(frame)

    assert len(events) == 1
    assert isinstance(events[0], Frame)
    assert events[0].cmd == 0x7D
    assert events[0].payload == b"hello"

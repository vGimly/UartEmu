from protocol import Frame, FrameParser, encode_frame


def test_frame_split():
    parser = FrameParser()

    frame = encode_frame(0x01, b"hello")

    assert parser.feed(frame[:2]) == []
    assert parser.feed(frame[2:5]) == []

    events = parser.feed(frame[5:])

    assert len(events) == 1
    assert isinstance(events[0], Frame)

    assert events[0].cmd == 0x01
    assert events[0].payload == b"hello"


def test_two_frames_in_one_chunk():
    parser = FrameParser()

    data = (
        encode_frame(0x01, b"one") +
        encode_frame(0x01, b"two")
    )

    events = parser.feed(data)

    assert len(events) == 2

    assert events[0].payload == b"one"
    assert events[1].payload == b"two"

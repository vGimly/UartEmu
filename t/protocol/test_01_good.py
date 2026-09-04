from protocol import Frame, FrameParser, encode_frame


def parse(data):
    parser = FrameParser()

    events = parser.feed(data)

    assert len(events) == 1
    return events[0]


def test_empty_payload():
    event = parse(
        encode_frame(0x01, b"")
    )

    assert isinstance(event, Frame)
    assert event.cmd == 0x01
    assert event.payload == b""


def test_payload():
    event = parse(
        encode_frame(0x01, b"hello")
    )

    assert isinstance(event, Frame)
    assert event.cmd == 0x01
    assert event.payload == b"hello"


def test_binary_payload():
    payload = bytes(range(256))

    event = parse(
        encode_frame(0x01, payload)
    )

    assert isinstance(event, Frame)
    assert event.cmd == 0x01
    assert event.payload == payload

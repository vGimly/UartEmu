from protocol import Frame, FrameParser, encode_frame


def parse(data):
    parser = FrameParser()

    events = parser.feed(data)

    assert len(events) == 1
    return events[0]


def test_payload_1():
    payload = b"x"

    event = parse(encode_frame(0x01, payload))

    assert isinstance(event, Frame)
    assert event.payload == payload


def test_payload_255():
    payload = bytes(range(255))

    event = parse(encode_frame(0x01, payload))

    assert isinstance(event, Frame)
    assert event.payload == payload


def test_payload_1024():
    payload = bytes(range(256)) * 4

    event = parse(encode_frame(0x01, payload))

    assert isinstance(event, Frame)
    assert event.payload == payload


def test_payload_4096():
    payload = bytes(range(256)) * 16

    event = parse(encode_frame(0x01, payload))

    assert isinstance(event, Frame)
    assert event.payload == payload

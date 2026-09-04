from protocol import Frame, FrameParser, encode_frame, calc_crc


def parse(data):
    parser = FrameParser()

    events = parser.feed(data)

    assert len(events) == 1
    return events[0]


def escaped(cmd, payload, crc):
    data = bytes([cmd]) + payload + crc

    result = bytearray()

    for byte in data:
        if byte == 0x7E:
            result.extend(b"\x7d\x5e")
        elif byte == 0x7D:
            result.extend(b"\x7d\x5d")
        else:
            result.append(byte)

    return b"\x7e" + bytes(result) + b"\x7e"


def test_crc_escape():
    for value in range(65536):
        payload = value.to_bytes(2, "big")

        crc = calc_crc(0x01, payload)

        crc_bytes = crc.to_bytes(2, "big")

        if 0x7D not in crc_bytes and 0x7E not in crc_bytes:
            continue

        frame = encode_frame(0x01, payload)

        # Кадр должен содержать escape-последовательность,
        # соответствующую найденному байту CRC.
        for byte in crc_bytes:
            if byte == 0x7D:
                assert b"\x7d\x5d" in frame
            elif byte == 0x7E:
                assert b"\x7d\x5e" in frame

        assert frame == escaped(
            0x01,
            payload,
            crc_bytes,
        )

        event = parse(frame)

        assert isinstance(event, Frame)
        assert event.cmd == 0x01
        assert event.payload == payload
        assert event.crc == crc

        return

    raise AssertionError("no CRC containing 0x7d or 0x7e found")

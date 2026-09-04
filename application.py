def command(client, cmd, payload):
    if cmd == 0x01:
        return b"OK=" + payload

    return None

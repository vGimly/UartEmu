"""
device: generic
version: 1.0.0
description: Default echo, register, and date-time protocol.
"""

import datetime

from protocol import BaseProtocol


class Protocol(BaseProtocol):
    def command(self, cmd, payload):
        if cmd == 0x01:
            return b"OK=" + payload

        if cmd == 0x02:
            return self.register_read_write(cmd, payload)

        if cmd == 0x03:
            return datetime.datetime.now().strftime("%Y%m%d %H%M%S").encode("ascii")

        return None

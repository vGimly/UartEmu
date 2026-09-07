"""
device: pzbx_br850-r0
version: 1.0.1
description: Protocol for PZBX BR850 rev.0 identification and echo tests.
"""

from protocol import BaseProtocol


class Protocol(BaseProtocol):
    def command(self, cmd, payload):
        if cmd == 0x01:
            return b"OK=" + payload

        if cmd == 0x20:
            return b"pzbx_br850-r0"

        return None

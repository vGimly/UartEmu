import asyncio
import logging

import app_loader
import registry

from protocol import CMD_IDENTIFY, Frame, FrameError, ProtocolError, encode_error, encode_frame, FrameParser
from state import DeviceState


log = logging.getLogger("uart")


class UARTServer:
    def __init__(self, host="10.9.0.1", port=7000):
        self.host = host
        self.port = port
        self.server = None
        self.clients = {}
        self.traffic_logging = True
        self.protocols = {}
        self.state = DeviceState()

    async def start(self):
        self.server = await asyncio.start_server(self.client_connected, self.host, self.port)
        log.info("UART server listening on %s:%d", self.host, self.port)

    async def stop(self):
        for writer in list(self.clients):
            writer.close()
        for writer in list(self.clients):
            try:
                await writer.wait_closed()
            except Exception:
                pass
        self.clients.clear()
        self.protocols.clear()
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def client_connected(self, reader, writer):
        peer = writer.get_extra_info("peername")
        host = peer[0] if peer else "unknown"
        port = peer[1] if peer else 0
        client_key = registry.record_connect(host, port)
        self.clients[writer] = client_key
        log.info("client connected: %s key=%s", peer, client_key)

        parser = FrameParser()
        try:
            while True:
                try:
                    data = await asyncio.wait_for(reader.read(4096), timeout=parser.timeout)
                except asyncio.TimeoutError:
                    event = parser.timeout_expired()
                    if event is not None:
                        await self.handle_event(writer, peer, client_key, event)
                    continue

                if not data:
                    break

                self.log_traffic("RX", peer, data)
                for event in parser.feed(data):
                    await self.handle_event(writer, peer, client_key, event)

        except ConnectionError as exc:
            log.info("client connection error %s: %s", peer, exc)
        except Exception:
            log.exception("client handler failed: %s", peer)
        finally:
            self.clients.pop(writer, None)
            self.protocols.pop(client_key, None)
            registry.record_disconnect(client_key)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            log.info("client disconnected: %s key=%s", peer, client_key)

    async def handle_event(self, writer, peer, client_key, event):
        if isinstance(event, Frame):
            registry.record_request(client_key)
            log.info(
                "FRAME %s key=%s: cmd=0x%02x payload=%s crc=0x%04x",
                peer, client_key, event.cmd, event.payload.hex(" "), event.crc,
            )
            await self.handle_frame(writer, peer, client_key, event)
            return

        if isinstance(event, FrameError):
            log.warning(
                "FRAME ERROR %s key=%s: code=0x%02x %s",
                peer, client_key, event.code, event.detail,
            )
            await self.send_error(writer, peer, client_key, event.code)

    async def inject_event(self, cmd, payload, exclude=None):
        data = encode_frame(cmd, payload)
        count = 0
        for writer in list(self.clients):
            if writer is exclude:
                continue
            peer = writer.get_extra_info("peername")
            client_key = self.clients[writer]
            try:
                writer.write(data)
                await writer.drain()
                registry.record_response(client_key)
                count += 1
                self.log_traffic("TX", peer, data)
            except Exception:
                log.exception("event delivery failed: %s", peer)
        return count

    def get_protocol(self, client_key):
        protocol_name = registry.protocol_for_client(client_key)
        entry = self.protocols.get(client_key)
        if entry is not None and entry[0] == protocol_name:
            return entry[1]

        client = registry.get_client(client_key)
        if client is None:
            return None

        protocol = app_loader.create(protocol_name, client, self.state)
        self.protocols[client_key] = (protocol_name, protocol)
        return protocol

    async def handle_frame(self, writer, peer, client_key, frame):
        if frame.cmd == CMD_IDENTIFY:
            await self.handle_identify(writer, peer, client_key, frame.payload)
            return

        protocol = self.get_protocol(client_key)
        if protocol is None:
            log.warning("no protocol for client %s", client_key)
            return

        try:
            answer = protocol.command(frame.cmd, frame.payload)
        except ProtocolError as exc:
            log.warning(
                "APPLICATION ERROR %s key=%s cmd=0x%02x: %s",
                peer, client_key, frame.cmd, exc,
            )
            answer = exc.payload()

        if answer is None:
            log.warning("unknown command %s: 0x%02x", peer, frame.cmd)
            return

        await self.send(writer, peer, client_key, encode_frame(frame.cmd, answer))

    async def handle_identify(self, writer, peer, client_key, payload):
        try:
            identity = payload.decode("utf-8")
        except UnicodeDecodeError:
            await self.send(writer, peer, client_key, encode_frame(CMD_IDENTIFY, b"E-INVALID_UTF8"))
            return

        if not identity:
            await self.send(writer, peer, client_key, encode_frame(CMD_IDENTIFY, b"E-EMPTY_ID"))
            return

        client = registry.identify_client(client_key, identity)
        if client is None:
            log.warning("unknown device identity %r for client %s", identity, client_key)
            await self.send(writer, peer, client_key, encode_frame(CMD_IDENTIFY, b"E-UNKNOWN_DEVICE"))
            return

        self.protocols.pop(client_key, None)
        log.info(
            "client identified: key=%s identity=%s device=%s protocol=%s",
            client_key, identity, client["device_id"], client["device_protocol"],
        )
        await self.send(writer, peer, client_key, encode_frame(CMD_IDENTIFY, b""))

    async def send_error(self, writer, peer, client_key, error_code):
        await self.send(writer, peer, client_key, encode_error(error_code))

    async def send(self, writer, peer, client_key, data):
        writer.write(data)
        await writer.drain()
        registry.record_response(client_key)
        self.log_traffic("TX", peer, data)

    def log_traffic(self, direction, peer, data):
        if not self.traffic_logging:
            return
        log.debug("%s %s: %s", direction, peer, data.hex(" "))

    @property
    def client_count(self):
        return len(self.clients)

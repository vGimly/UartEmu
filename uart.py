import asyncio
import logging
import app_loader
import registry

from protocol import (
    Frame,
    FrameParser,
    ProtocolError,
    encode_error,
    encode_frame,
)


log = logging.getLogger("uart")


class UARTServer:
    def __init__(self, host="10.9.0.1", port=7000):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()

        # Traffic logging can be changed at runtime through API.
        self.traffic_logging = True

    async def start(self):
        self.server = await asyncio.start_server(
            self.client_connected,
            self.host,
            self.port,
        )

        log.info(
            "UART server listening on %s:%d",
            self.host,
            self.port,
        )

    async def stop(self):
        for writer in list(self.clients):
            writer.close()

        for writer in list(self.clients):
            try:
                await writer.wait_closed()
            except Exception:
                pass

        self.clients.clear()

        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def client_connected(self, reader, writer):
        self.clients.add(writer)

        peer = writer.get_extra_info("peername")
        host = peer[0] if peer else "unknown"
        port = peer[1] if peer else 0

        registry.record_connect(host, port)

        log.info(
            "client connected: %s",
            peer,
        )

        parser = FrameParser()

        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(4096),
                        timeout=parser.timeout,
                    )

                except asyncio.TimeoutError:
                    event = parser.timeout_expired()

                    if event is not None:
                        await self.handle_event(
                            writer,
                            peer,
                            event,
                        )

                    continue

                if not data:
                    break

                self.log_traffic("RX", peer, data)

                for event in parser.feed(data):
                    await self.handle_event(
                        writer,
                        peer,
                        event,
                    )

        except ConnectionError as exc:
            log.info(
                "client connection error %s: %s",
                peer,
                exc,
            )

        except Exception:
            log.exception(
                "client handler failed: %s",
                peer,
            )

        finally:
            self.clients.discard(writer)

            registry.record_disconnect(host)

            writer.close()

            try:
                await writer.wait_closed()
            except Exception:
                pass

            log.info(
                "client disconnected: %s",
                peer,
            )

    async def handle_event(self, writer, peer, event):
        if isinstance(event, Frame):
            log.info(
                "FRAME %s: cmd=0x%02x payload=%s crc=0x%04x",
                peer,
                event.cmd,
                event.payload.hex(" "),
                event.crc,
            )

            await self.handle_frame(
                writer,
                peer,
                event,
            )

        elif isinstance(event, ProtocolError):
            log.warning(
                "PROTOCOL ERROR %s: code=0x%02x %s",
                peer,
                event.code,
                event.detail,
            )

            await self.send_error(
                writer,
                peer,
                event.code,
            )

    async def inject_event(self, cmd, payload, exclude=None):
        data = encode_frame(cmd, payload)

        clients = list(self.clients)

        log.info(
            "EVENT cmd=0x%02x payload=%s clients=%d",
            cmd,
            payload.hex(" "),
            len(clients),
        )

        count = 0

        for writer in clients:
            if writer is exclude:
                continue

            peer = writer.get_extra_info("peername")

            try:
                writer.write(data)
                await writer.drain()

                count += 1

                log.info(
                    "EVENT TX %s: cmd=0x%02x payload=%s",
                    peer,
                    cmd,
                    payload.hex(" "),
                )

                if self.traffic_logging:
                    log.debug(
                        "TX %s: %s",
                        peer,
                        data.hex(" "),
                    )

            except Exception:
                log.exception(
                    "event delivery failed: %s",
                    peer,
                )

        return count

    async def handle_frame(self, writer, peer, frame):
        host = peer[0] if peer else "unknown"
        protocol = registry.protocol_for_host(host)

        answer = app_loader.command(
            protocol,
            peer,
            frame.cmd,
            frame.payload,
        )

        if answer is None:
            log.warning(
                "unknown command %s: 0x%02x",
                peer,
                frame.cmd,
            )
            return

        data = encode_frame(frame.cmd, answer)

        await self.send(writer, peer, data)

    async def send_error(self, writer, peer, error_code):
        data = encode_error(error_code)

        await self.send(
            writer,
            peer,
            data,
        )

    async def send(self, writer, peer, data):
        writer.write(data)
        await writer.drain()

        self.log_traffic(
            "TX",
            peer,
            data,
        )

    def log_traffic(self, direction, peer, data):
        if not self.traffic_logging:
            return

        log.debug(
            "%s %s: %s",
            direction,
            peer,
            data.hex(" "),
        )

    @property
    def client_count(self):
        return len(self.clients)

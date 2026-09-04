import asyncio
import logging


log = logging.getLogger("uart")


class UARTServer:
    def __init__(self, host="10.9.0.1", port=7000):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()

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
        log.info("client connected: %s", peer)

        try:
            while True:
                data = await reader.read(4096)

                if not data:
                    break

                log.debug(
                    "RX %s: %s",
                    peer,
                    data.hex(" "),
                )

                # Пока просто echo для проверки транспорта.
                # Позже здесь будет parser.
                writer.write(data)
                await writer.drain()

        finally:
            self.clients.discard(writer)

            writer.close()

            try:
                await writer.wait_closed()
            except Exception:
                pass

            log.info("client disconnected: %s", peer)

    @property
    def client_count(self):
        return len(self.clients)

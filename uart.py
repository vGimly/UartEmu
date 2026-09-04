import asyncio


class UARTServer:
    def __init__(self, host="127.0.0.1", port=7000):
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

        print(f"UART server listening on {self.host}:{self.port}")

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
        print(f"UART client connected: {peer}")

        try:
            while True:
                data = await reader.read(4096)

                if not data:
                    break

                print(f"RX {data.hex()}")

        finally:
            self.clients.discard(writer)

            writer.close()

            try:
                await writer.wait_closed()
            except Exception:
                pass

            print(f"UART client disconnected: {peer}")

    @property
    def client_count(self):
        return len(self.clients)

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import router
from uart import UARTServer


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

uart = UARTServer(host="10.9.0.1", port=7000)


@asynccontextmanager
async def lifespan(app):
    app.state.uart = uart

    await uart.start()

    yield

    await uart.stop()


app = FastAPI(
    title="UART Emulator",
    version="0.1.0",
    root_path="/uart",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")

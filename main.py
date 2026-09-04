from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import router
from uart import UARTServer


uart = UARTServer()


@asynccontextmanager
async def lifespan(app):
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

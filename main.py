import logging
import sys

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api import router, set_uart_server
from uart import UARTServer

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("uart.log"),
    ],
)

uart = UARTServer(host="10.9.0.1", port=7000)
set_uart_server(uart)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "UART Emulator"},
    )


@app.get("/devices/{device_id}", response_class=HTMLResponse)
async def device(request: Request, device_id: int):
    if request.app.state.uart.state is None:
        return HTMLResponse("Device state is unavailable", status_code=503)
    return templates.TemplateResponse(
        request=request,
        name="device.html",
        context={"title": "Device state", "device_id": device_id},
    )

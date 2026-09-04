from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter()


class LoggingConfig(BaseModel):
    traffic: bool


@router.get("/logging")
async def get_logging(request: Request):
    uart = request.app.state.uart

    return {
        "traffic": uart.traffic_logging,
    }


@router.put("/logging")
async def set_logging(
    config: LoggingConfig,
    request: Request,
):
    uart = request.app.state.uart
    uart.traffic_logging = config.traffic

    return {
        "traffic": uart.traffic_logging,
    }


@router.get("/status")
async def status(request: Request):
    uart = request.app.state.uart

    return {
        "status": "ok",
        "clients": uart.client_count,
    }

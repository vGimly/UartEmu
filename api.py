from fastapi import APIRouter, Request
from pydantic import BaseModel, Field


router = APIRouter()


class EventRequest(BaseModel):
    cmd: int = Field(..., ge=0, le=255)
    payload: str = ""


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


@router.post("/event")
async def inject_event(event: EventRequest):
    try:
        payload = bytes.fromhex(event.payload)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="payload must be hexadecimal",
        )

    count = await uart_server.inject_event(
        event.cmd,
        payload,
    )

    return {
        "cmd": event.cmd,
        "payload": event.payload,
        "clients": count,
    }

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import app_loader
import registry

router = APIRouter()

uart = None


def set_uart_server(server):
    global uart
    uart = server


class EventRequest(BaseModel):
    cmd: int = Field(..., ge=0, le=255)
    payload: str = ""


class LoggingConfig(BaseModel):
    traffic: bool


class DeviceCreate(BaseModel):
    name: str
    protocol: str = "application"
    description: str = ""


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    protocol: Optional[str] = None
    description: Optional[str] = None


class ClientCreate(BaseModel):
    host: str
    port: int = 0
    device_id: Optional[int] = None


class ClientAssign(BaseModel):
    device_id: Optional[int] = None


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

    count = await uart.inject_event(
        event.cmd,
        payload,
    )

    return {
        "cmd": event.cmd,
        "payload": event.payload,
        "clients": count,
    }


@router.put("/reload_app")
async def reload_app(protocol: Optional[str] = None):
    try:
        app_loader.reload(protocol)
    except Exception:
        logging.exception("application reload failed")
        raise HTTPException(
            status_code=500,
            detail="application reload failed",
        )

    return {
        "status": "ok",
    }


@router.get("/state")
async def get_state(protocol: str = "application"):
    return app_loader.dump_state(protocol)


@router.get("/protocols")
async def list_protocols():
    return app_loader.list_protocols()


# ---------------------------------------------------------------- devices


@router.get("/devices")
async def list_devices():
    return registry.list_devices()


@router.post("/devices")
async def create_device(device: DeviceCreate):
    if not app_loader.validate_protocol(device.protocol):
        raise HTTPException(
            status_code=400,
            detail="unknown protocol module: %s" % device.protocol,
        )

    created = registry.create_device(
        device.name,
        device.protocol,
        device.description,
    )

    if created is None:
        raise HTTPException(
            status_code=409,
            detail="device already exists",
        )

    return created


@router.get("/devices/{device_id}")
async def get_device(device_id: int):
    device = registry.get_device(device_id)

    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    return device


@router.put("/devices/{device_id}")
async def update_device(device_id: int, device: DeviceUpdate):
    if device.protocol is not None and not app_loader.validate_protocol(
        device.protocol
    ):
        raise HTTPException(
            status_code=400,
            detail="unknown protocol module: %s" % device.protocol,
        )

    updated = registry.update_device(
        device_id,
        name=device.name,
        protocol=device.protocol,
        description=device.description,
    )

    if updated is None:
        raise HTTPException(status_code=404, detail="device not found")

    return updated


@router.delete("/devices/{device_id}")
async def delete_device(device_id: int):
    if not registry.delete_device(device_id):
        raise HTTPException(status_code=404, detail="device not found")

    return {
        "status": "ok",
    }


# ---------------------------------------------------------------- clients


@router.get("/clients")
async def list_clients():
    return registry.list_clients()


@router.post("/clients")
async def create_client(client: ClientCreate):
    if client.device_id is not None and registry.get_device(client.device_id) is None:
        raise HTTPException(status_code=404, detail="device not found")

    created = registry.create_client(
        client.host,
        client.port,
        client.device_id,
    )

    if created is None:
        raise HTTPException(status_code=409, detail="client already exists")

    return created


@router.get("/clients/{host}")
async def get_client(host: str):
    client = registry.get_client(host)

    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    return client


@router.put("/clients/{host}")
async def assign_client(host: str, assignment: ClientAssign):
    if (
        assignment.device_id is not None
        and registry.get_device(assignment.device_id) is None
    ):
        raise HTTPException(status_code=404, detail="device not found")

    updated = registry.assign_device(host, assignment.device_id)

    if updated is None:
        raise HTTPException(status_code=404, detail="client not found")

    return updated


@router.delete("/clients/{host}")
async def delete_client(host: str):
    if not registry.delete_client(host):
        raise HTTPException(status_code=404, detail="client not found")

    return {
        "status": "ok",
    }

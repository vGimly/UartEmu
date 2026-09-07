import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import app_loader
import registry

router = APIRouter()


class EventRequest(BaseModel):
    cmd: int = Field(..., ge=0, le=255)
    payload: str = ""


class LoggingConfig(BaseModel):
    traffic: bool


class DeviceCreate(BaseModel):
    name: str
    identity: Optional[str] = None
    protocol: str = "default"
    description: str = ""


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    identity: Optional[str] = None
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
    return {"traffic": uart.traffic_logging}


@router.put("/logging")
async def set_logging(config: LoggingConfig, request: Request):
    uart = request.app.state.uart
    uart.traffic_logging = config.traffic
    return {"traffic": uart.traffic_logging}


@router.get("/status")
async def status(request: Request):
    uart = request.app.state.uart
    return {"status": "ok", "clients": uart.client_count}


@router.post("/event")
async def inject_event(event: EventRequest, request: Request):
    try:
        payload = bytes.fromhex(event.payload)
    except ValueError:
        raise HTTPException(status_code=400, detail="payload must be hexadecimal")

    count = await request.app.state.uart.inject_event(event.cmd, payload)
    return {"cmd": event.cmd, "payload": event.payload, "clients": count}


@router.put("/reload_app")
async def reload_app(protocol: Optional[str] = None):
    try:
        app_loader.reload(protocol)
    except Exception:
        logging.exception("application reload failed")
        raise HTTPException(status_code=500, detail="application reload failed")
    return {"status": "ok"}


@router.get("/state/{device_id}")
async def get_state(device_id: int):
    device = registry.get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    return app_loader.dump_state(device["protocol"], device_id)


@router.get("/protocols")
async def list_protocols():
    return app_loader.list_protocols()


@router.get("/devices")
async def list_devices():
    return registry.list_devices()


@router.post("/devices")
async def create_device(device: DeviceCreate):
    if not app_loader.validate_protocol(device.protocol):
        raise HTTPException(status_code=400, detail="unknown protocol module: %s" % device.protocol)

    created = registry.create_device(
        device.name,
        device.protocol,
        device.description,
        device.identity,
    )
    if created is None:
        raise HTTPException(status_code=409, detail="device name or identity already exists")
    return created


@router.get("/devices/{device_id}")
async def get_device(device_id: int):
    device = registry.get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    return device


@router.put("/devices/{device_id}")
async def update_device(device_id: int, device: DeviceUpdate):
    if device.protocol is not None and not app_loader.validate_protocol(device.protocol):
        raise HTTPException(status_code=400, detail="unknown protocol module: %s" % device.protocol)

    updated = registry.update_device(
        device_id,
        name=device.name,
        identity=device.identity,
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
    return {"status": "ok"}


@router.get("/clients")
async def list_clients():
    return registry.list_clients()


@router.post("/clients")
async def create_client(client: ClientCreate):
    if client.device_id is not None and registry.get_device(client.device_id) is None:
        raise HTTPException(status_code=404, detail="device not found")
    return registry.create_client(client.host, client.port, client.device_id)


@router.get("/clients/{client_key}")
async def get_client(client_key: str):
    client = registry.get_client(client_key)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return client


@router.put("/clients/{client_key}")
async def assign_client(client_key: str, assignment: ClientAssign):
    if assignment.device_id is not None and registry.get_device(assignment.device_id) is None:
        raise HTTPException(status_code=404, detail="device not found")
    updated = registry.assign_device(client_key, assignment.device_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="client not found")
    return updated


@router.delete("/clients/{client_key}")
async def delete_client(client_key: str):
    if not registry.delete_client(client_key):
        raise HTTPException(status_code=404, detail="client not found")
    return {"status": "ok"}

from fastapi import FastAPI

from api import router


app = FastAPI(
    title="UART Emulator",
    version="0.1.0",
    root_path="/uart",
)

app.include_router(router, prefix="/api")

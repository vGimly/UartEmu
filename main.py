from fastapi import FastAPI

app = FastAPI(title="UART Emulator")


@app.get("/")
async def root():
    return {"status": "ok"}

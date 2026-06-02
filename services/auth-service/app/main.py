import logging

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)

app = FastAPI(title="FoodFlow Auth Service", version="0.1.0")
app.include_router(api_router)


@app.get("/health")
async def health() -> dict:
    return {"service": "auth-service", "status": "ok"}

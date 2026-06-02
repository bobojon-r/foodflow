from fastapi import APIRouter

from app.api.v1.routes import menu, restaurants

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(restaurants.router)
api_router.include_router(menu.router)

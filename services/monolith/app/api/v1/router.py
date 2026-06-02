from fastapi import APIRouter

from app.api.v1.routes import auth, menu, orders, restaurants

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(restaurants.router)
api_router.include_router(menu.router)
api_router.include_router(orders.router)

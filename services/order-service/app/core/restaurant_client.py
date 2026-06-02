from decimal import Decimal

import httpx

from app.core.config import settings


class RestaurantServiceError(Exception):
    pass


class RestaurantClient:
    """HTTP client for communicating with restaurant-service."""

    def __init__(self) -> None:
        self._base_url = settings.RESTAURANT_SERVICE_URL

    async def get_restaurant(self, restaurant_id: int) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self._base_url}/api/v1/restaurants/{restaurant_id}")
        if response.status_code == 404:
            raise RestaurantServiceError(f"Restaurant {restaurant_id} not found")
        if response.status_code != 200:
            raise RestaurantServiceError(f"Restaurant service error: {response.status_code}")
        return response.json()

    async def get_menu_items(self, restaurant_id: int, item_ids: list[int]) -> dict[int, Decimal]:
        """Return {item_id: price} for available items in the restaurant."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self._base_url}/api/v1/restaurants/{restaurant_id}/menu/")
        if response.status_code != 200:
            raise RestaurantServiceError(f"Restaurant service error: {response.status_code}")

        items = {item["id"]: Decimal(str(item["price"])) for item in response.json() if item["is_available"]}
        missing = set(item_ids) - set(items.keys())
        if missing:
            raise RestaurantServiceError(f"Menu items not found or unavailable: {missing}")
        return {iid: items[iid] for iid in item_ids}


restaurant_client = RestaurantClient()

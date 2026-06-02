import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, role: str = "restaurant_owner") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret123", "full_name": "Owner", "role": role},
    )
    login = await client.post("/api/v1/auth/login", data={"username": email, "password": "secret123"})
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_create_restaurant(client: AsyncClient):
    token = await _register_and_login(client, "owner@example.com")
    response = await client.post(
        "/api/v1/restaurants/",
        json={"name": "Pizza Place", "address": "123 Main St"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Pizza Place"


@pytest.mark.asyncio
async def test_customer_cannot_create_restaurant(client: AsyncClient):
    token = await _register_and_login(client, "customer@example.com", role="customer")
    response = await client.post(
        "/api/v1/restaurants/",
        json={"name": "Fail Place", "address": "Nowhere"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_restaurants(client: AsyncClient):
    token = await _register_and_login(client, "owner2@example.com")
    await client.post(
        "/api/v1/restaurants/",
        json={"name": "Sushi Bar", "address": "456 Oak Ave"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get("/api/v1/restaurants/")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_update_restaurant(client: AsyncClient):
    token = await _register_and_login(client, "owner3@example.com")
    create = await client.post(
        "/api/v1/restaurants/",
        json={"name": "Burger Joint", "address": "789 Elm St"},
        headers={"Authorization": f"Bearer {token}"},
    )
    rid = create.json()["id"]
    response = await client.patch(
        f"/api/v1/restaurants/{rid}",
        json={"name": "Super Burger Joint"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Super Burger Joint"

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient):
    """Create owner, customer, restaurant, and menu item. Return tokens and ids."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "pass123", "full_name": "Owner", "role": "restaurant_owner"},
    )
    owner_login = await client.post(
        "/api/v1/auth/login", data={"username": "owner@example.com", "password": "pass123"}
    )
    owner_token = owner_login.json()["access_token"]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "customer@example.com", "password": "pass123", "full_name": "Customer", "role": "customer"},
    )
    cust_login = await client.post(
        "/api/v1/auth/login", data={"username": "customer@example.com", "password": "pass123"}
    )
    cust_token = cust_login.json()["access_token"]

    restaurant = await client.post(
        "/api/v1/restaurants/",
        json={"name": "Test Restaurant", "address": "1 Test St"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    rid = restaurant.json()["id"]

    item = await client.post(
        f"/api/v1/restaurants/{rid}/menu/",
        json={"name": "Burger", "price": "9.99"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    iid = item.json()["id"]

    return owner_token, cust_token, rid, iid


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    owner_token, cust_token, rid, iid = await _setup(client)
    response = await client.post(
        "/api/v1/orders/",
        json={"restaurant_id": rid, "delivery_address": "My Home", "items": [{"menu_item_id": iid, "quantity": 2}]},
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert float(data["total_price"]) == pytest.approx(19.98)
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_cancel_order(client: AsyncClient):
    owner_token, cust_token, rid, iid = await _setup(client)
    order = await client.post(
        "/api/v1/orders/",
        json={"restaurant_id": rid, "delivery_address": "My Home", "items": [{"menu_item_id": iid, "quantity": 1}]},
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    oid = order.json()["id"]
    response = await client.delete(f"/api/v1/orders/{oid}", headers={"Authorization": f"Bearer {cust_token}"})
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_owner_updates_order_status(client: AsyncClient):
    owner_token, cust_token, rid, iid = await _setup(client)
    order = await client.post(
        "/api/v1/orders/",
        json={"restaurant_id": rid, "delivery_address": "My Home", "items": [{"menu_item_id": iid, "quantity": 1}]},
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    oid = order.json()["id"]
    response = await client.patch(
        f"/api/v1/orders/{oid}/status",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

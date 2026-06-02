import pytest
from httpx import AsyncClient


ORDER_PAYLOAD = {
    "restaurant_id": 1,
    "delivery_address": "Home St 1",
    "items": [{"menu_item_id": 1, "quantity": 2}, {"menu_item_id": 2, "quantity": 1}],
}


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    r = await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert float(data["total_price"]) == pytest.approx(25.00)  # 2*10 + 1*5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_order_items_empty(client: AsyncClient):
    r = await client.post("/api/v1/orders/", json={
        "restaurant_id": 1, "delivery_address": "X", "items": []
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient):
    await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    r = await client.get("/api/v1/orders/")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_order(client: AsyncClient):
    create = await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    oid = create.json()["id"]
    r = await client.get(f"/api/v1/orders/{oid}")
    assert r.status_code == 200
    assert r.json()["id"] == oid


@pytest.mark.asyncio
async def test_cancel_order(client: AsyncClient):
    create = await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    oid = create.json()["id"]
    r = await client.delete(f"/api/v1/orders/{oid}")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_cancel_non_pending_order(client: AsyncClient):
    create = await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    oid = create.json()["id"]
    await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "confirmed"})
    r = await client.delete(f"/api/v1/orders/{oid}")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_status(client: AsyncClient):
    create = await client.post("/api/v1/orders/", json=ORDER_PAYLOAD)
    oid = create.json()["id"]
    r = await client.patch(f"/api/v1/orders/{oid}/status", json={"status": "confirmed"})
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

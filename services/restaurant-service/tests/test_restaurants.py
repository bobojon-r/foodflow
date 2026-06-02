import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_restaurant(client: AsyncClient):
    r = await client.post("/api/v1/restaurants/", json={
        "name": "Pizza House", "address": "Main St 1"
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Pizza House"
    assert r.json()["owner_id"] == 1


@pytest.mark.asyncio
async def test_list_restaurants(client: AsyncClient):
    await client.post("/api/v1/restaurants/", json={"name": "A", "address": "Addr A"})
    await client.post("/api/v1/restaurants/", json={"name": "B", "address": "Addr B"})
    r = await client.get("/api/v1/restaurants/")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_restaurant(client: AsyncClient):
    create = await client.post("/api/v1/restaurants/", json={"name": "Solo", "address": "X"})
    rid = create.json()["id"]
    r = await client.get(f"/api/v1/restaurants/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid


@pytest.mark.asyncio
async def test_get_restaurant_not_found(client: AsyncClient):
    r = await client.get("/api/v1/restaurants/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_restaurant(client: AsyncClient):
    create = await client.post("/api/v1/restaurants/", json={"name": "Old Name", "address": "X"})
    rid = create.json()["id"]
    r = await client.patch(f"/api/v1/restaurants/{rid}", json={"name": "New Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_restaurant(client: AsyncClient):
    create = await client.post("/api/v1/restaurants/", json={"name": "To Delete", "address": "X"})
    rid = create.json()["id"]
    r = await client.delete(f"/api/v1/restaurants/{rid}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/v1/restaurants/{rid}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_create_menu_item(client: AsyncClient):
    rest = await client.post("/api/v1/restaurants/", json={"name": "R", "address": "A"})
    rid = rest.json()["id"]
    r = await client.post(f"/api/v1/restaurants/{rid}/menu/", json={
        "name": "Burger", "price": "9.99"
    })
    assert r.status_code == 201
    assert float(r.json()["price"]) == pytest.approx(9.99)


@pytest.mark.asyncio
async def test_menu_item_negative_price(client: AsyncClient):
    rest = await client.post("/api/v1/restaurants/", json={"name": "R", "address": "A"})
    rid = rest.json()["id"]
    r = await client.post(f"/api/v1/restaurants/{rid}/menu/", json={
        "name": "Burger", "price": "-5.00"
    })
    assert r.status_code == 422

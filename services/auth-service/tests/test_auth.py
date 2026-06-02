import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json={
        "email": "user@example.com", "password": "pass123", "full_name": "User"
    })
    assert r.status_code == 201
    assert r.json()["email"] == "user@example.com"
    assert r.json()["role"] == "customer"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "pass123", "full_name": "Dup"}
    await client.post("/api/v1/auth/register", json=payload)
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "password": "pass123", "full_name": "User"
    })
    r = await client.post("/api/v1/auth/login", data={
        "username": "login@example.com", "password": "pass123"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com", "password": "pass123", "full_name": "User"
    })
    r = await client.post("/api/v1/auth/login", data={
        "username": "wrong@example.com", "password": "badpass"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "me@example.com", "password": "pass123", "full_name": "Me"
    })
    login = await client.post("/api/v1/auth/login", data={
        "username": "me@example.com", "password": "pass123"
    })
    token = login.json()["access_token"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_register_owner_role(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json={
        "email": "owner@example.com", "password": "pass123",
        "full_name": "Owner", "role": "restaurant_owner"
    })
    assert r.status_code == 201
    assert r.json()["role"] == "restaurant_owner"

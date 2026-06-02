from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import TokenUser, UserRole, get_current_user, require_restaurant_owner
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

MOCK_RESTAURANT = {"id": 1, "name": "Test", "is_active": True}
MOCK_PRICES = {1: Decimal("10.00"), 2: Decimal("5.00")}


def make_customer(user_id: int = 1) -> TokenUser:
    return TokenUser(user_id=user_id, role=UserRole.CUSTOMER)


def make_owner(user_id: int = 2) -> TokenUser:
    return TokenUser(user_id=user_id, role=UserRole.RESTAURANT_OWNER)


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: make_customer()
    app.dependency_overrides[require_restaurant_owner] = lambda: make_owner()

    with (
        patch("app.api.v1.routes.orders.restaurant_client.get_restaurant", new=AsyncMock(return_value=MOCK_RESTAURANT)),
        patch("app.api.v1.routes.orders.restaurant_client.get_menu_items", new=AsyncMock(return_value=MOCK_PRICES)),
        patch("app.api.v1.routes.orders.publish", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
    await engine.dispose()

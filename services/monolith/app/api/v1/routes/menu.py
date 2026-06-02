from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_restaurant_owner
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.menu_item import MenuItemCreate, MenuItemRead, MenuItemUpdate

router = APIRouter(prefix="/restaurants/{restaurant_id}/menu", tags=["menu"])


async def _get_owned_restaurant(restaurant_id: int, owner: User, db: AsyncSession) -> Restaurant:
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    if restaurant.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your restaurant")
    return restaurant


@router.get("/", response_model=list[MenuItemRead])
async def list_menu_items(restaurant_id: int, db: AsyncSession = Depends(get_db)) -> list[MenuItem]:
    result = await db.execute(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id, MenuItem.is_available == True)  # noqa: E712
    )
    return list(result.scalars().all())


@router.post("/", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    restaurant_id: int,
    payload: MenuItemCreate,
    current_user: User = Depends(require_restaurant_owner),
    db: AsyncSession = Depends(get_db),
) -> MenuItem:
    await _get_owned_restaurant(restaurant_id, current_user, db)
    item = MenuItem(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=MenuItemRead)
async def update_menu_item(
    restaurant_id: int,
    item_id: int,
    payload: MenuItemUpdate,
    current_user: User = Depends(require_restaurant_owner),
    db: AsyncSession = Depends(get_db),
) -> MenuItem:
    await _get_owned_restaurant(restaurant_id, current_user, db)

    result = await db.execute(
        select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    restaurant_id: int,
    item_id: int,
    current_user: User = Depends(require_restaurant_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_owned_restaurant(restaurant_id, current_user, db)

    result = await db.execute(
        select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    await db.delete(item)
    await db.commit()

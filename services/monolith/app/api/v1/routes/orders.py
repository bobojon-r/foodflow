from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_restaurant_owner
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.restaurant import Restaurant
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == payload.restaurant_id, Restaurant.is_active == True)  # noqa: E712
    )
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    menu_item_ids = [item.menu_item_id for item in payload.items]
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id.in_(menu_item_ids),
            MenuItem.restaurant_id == payload.restaurant_id,
            MenuItem.is_available == True,  # noqa: E712
        )
    )
    menu_items = {item.id: item for item in result.scalars().all()}

    missing = set(menu_item_ids) - set(menu_items.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Menu items not found or unavailable: {missing}",
        )

    order = Order(
        customer_id=current_user.id,
        restaurant_id=payload.restaurant_id,
        delivery_address=payload.delivery_address,
    )
    db.add(order)
    await db.flush()

    total = 0
    for item_data in payload.items:
        menu_item = menu_items[item_data.menu_item_id]
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=menu_item.price,
        )
        db.add(order_item)
        total += menu_item.price * item_data.quantity

    order.total_price = total
    await db.commit()

    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.get("/", response_model=list[OrderRead])
async def list_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Order]:
    query = select(Order).options(selectinload(Order.items)).offset(skip).limit(limit)

    if current_user.role == UserRole.CUSTOMER:
        query = query.where(Order.customer_id == current_user.id)
    elif current_user.role == UserRole.RESTAURANT_OWNER:
        owned = await db.execute(select(Restaurant.id).where(Restaurant.owner_id == current_user.id))
        restaurant_ids = [r for r in owned.scalars().all()]
        query = query.where(Order.restaurant_id.in_(restaurant_ids))

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

    return order


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user: User = Depends(require_restaurant_owner),
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    owned = await db.execute(
        select(Restaurant).where(Restaurant.id == order.restaurant_id, Restaurant.owner_id == current_user.id)
    )
    if not owned.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your restaurant's order")

    order.status = payload.status
    await db.commit()
    await db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be cancelled",
        )

    order.status = OrderStatus.CANCELLED
    await db.commit()

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import TokenUser, UserRole, get_current_user, require_restaurant_owner
from app.core.kafka import publish
from app.core.restaurant_client import RestaurantServiceError, restaurant_client
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    current_user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    try:
        restaurant = await restaurant_client.get_restaurant(payload.restaurant_id)
    except RestaurantServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not restaurant.get("is_active"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restaurant is not active")

    item_ids = [i.menu_item_id for i in payload.items]
    try:
        prices = await restaurant_client.get_menu_items(payload.restaurant_id, item_ids)
    except RestaurantServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    order = Order(
        customer_id=current_user.id,
        restaurant_id=payload.restaurant_id,
        delivery_address=payload.delivery_address,
    )
    db.add(order)
    await db.flush()

    total = 0
    order_items_data = []
    for item_data in payload.items:
        price = prices[item_data.menu_item_id]
        db.add(OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=price,
        ))
        total += price * item_data.quantity
        order_items_data.append({
            "menu_item_id": item_data.menu_item_id,
            "quantity": item_data.quantity,
            "unit_price": str(price),
        })

    order.total_price = total
    await db.commit()

    await publish("order.created", {
        "order_id": order.id,
        "customer_id": current_user.id,
        "restaurant_id": payload.restaurant_id,
        "total_price": str(total),
        "delivery_address": payload.delivery_address,
        "items": order_items_data,
    })

    result = await db.execute(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))
    return result.scalar_one()


@router.get("/", response_model=list[OrderRead])
async def list_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Order]:
    query = select(Order).options(selectinload(Order.items)).offset(skip).limit(limit)
    if current_user.role == UserRole.CUSTOMER:
        query = query.where(Order.customer_id == current_user.id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    current_user: TokenUser = Depends(get_current_user),
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
    current_user: TokenUser = Depends(require_restaurant_owner),
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    old_status = order.status
    order.status = payload.status
    await db.commit()
    await db.refresh(order)

    await publish("order.status_changed", {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "restaurant_id": order.restaurant_id,
        "old_status": old_status,
        "new_status": payload.status,
    })

    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    current_user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending orders can be cancelled")

    old_status = order.status
    order.status = OrderStatus.CANCELLED
    await db.commit()

    await publish("order.status_changed", {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "restaurant_id": order.restaurant_id,
        "old_status": old_status,
        "new_status": OrderStatus.CANCELLED,
    })

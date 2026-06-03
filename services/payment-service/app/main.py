import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import stripe
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI

from app.api.v1.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.kafka import publish, start_producer, stop_producer
from app.core.observability import setup_observability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _create_payment_intent(order_id: str | int, amount_rub: float) -> str | None:
    """Create a Stripe PaymentIntent and return its id."""
    try:
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=int(amount_rub * 100),   # Stripe works in kopecks/cents
            currency="rub",
            # Test payment method — auto-confirms without 3DS in test mode
            payment_method="pm_card_visa",
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            metadata={"order_id": str(order_id)},
            idempotency_key=f"order-{order_id}",
        )
        logger.info(
            "PaymentIntent %s status=%s for order_id=%s",
            intent.id, intent.status, order_id,
        )

        # Publish directly when PaymentIntent is already succeeded.
        # In production with a real frontend the webhook would handle this;
        # here we auto-confirm with a test payment method so status is immediate.
        if intent.status == "succeeded":
            await publish("payment.succeeded", {
                "order_id": str(order_id),
                "amount": amount_rub,
                "stripe_payment_id": intent.id,
                "status": "succeeded",
            })

        return intent.id
    except stripe.StripeError as exc:
        logger.error("Stripe error for order_id=%s: %s", order_id, exc)
        return None


async def _consume() -> None:
    consumer = AIOKafkaConsumer(
        "order.created",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="payment-service",
        value_deserializer=lambda m: json.loads(m.decode()),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("Payment consumer started")
    try:
        async for msg in consumer:
            order = msg.value
            order_id = order.get("order_id")
            total = float(order.get("total_price", 0))
            logger.info("Processing payment for order_id=%s amount=%.2f", order_id, total)

            if settings.STRIPE_SECRET_KEY:
                await _create_payment_intent(order_id, total)
            else:
                logger.warning("STRIPE_SECRET_KEY not set — simulating payment for order_id=%s", order_id)
                await publish("payment.succeeded", {
                    "order_id": str(order_id),
                    "amount": total,
                    "status": "succeeded (simulated)",
                })
    except Exception:
        logger.exception("Consumer error")
    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        logger.info("Stripe initialized")

    await start_producer()
    consumer_task = asyncio.create_task(_consume())
    yield
    consumer_task.cancel()
    await stop_producer()


app = FastAPI(title="FoodFlow Payment Service", version="0.1.0", lifespan=lifespan)
app.include_router(webhooks_router)
setup_observability(app, "payment-service")


@app.get("/health")
async def health() -> dict:
    return {"service": "payment-service", "status": "ok"}

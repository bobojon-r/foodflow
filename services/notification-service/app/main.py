import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOPICS = ["order.created", "order.status_changed", "payment.succeeded"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"


settings = Settings()


def _handle(topic: str, value: dict) -> None:
    if topic == "order.created":
        logger.info("[NOTIFY] New order #%s from customer %s — total %s",
                    value.get("order_id"), value.get("customer_id"), value.get("total_price"))
    elif topic == "order.status_changed":
        logger.info("[NOTIFY] Order #%s status: %s → %s",
                    value.get("order_id"), value.get("old_status"), value.get("new_status"))
    elif topic == "payment.succeeded":
        logger.info("[NOTIFY] Payment succeeded for order #%s — amount %s",
                    value.get("order_id"), value.get("amount"))


async def _consume() -> None:
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="notification-service",
        value_deserializer=lambda m: json.loads(m.decode()),
        auto_offset_reset="earliest",
    )
    for attempt in range(1, 11):
        try:
            await consumer.start()
            break
        except KafkaConnectionError:
            logger.warning("Waiting for Kafka... attempt %d/10", attempt)
            await asyncio.sleep(5)
    else:
        logger.error("Could not connect to Kafka — notification consumer not started")
        return

    logger.info("Notification consumer started, listening: %s", TOPICS)
    try:
        async for msg in consumer:
            try:
                _handle(msg.topic, msg.value)
            except Exception:
                logger.exception("Failed to handle event: topic=%s", msg.topic)
    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    task = asyncio.create_task(_consume())
    yield
    task.cancel()


app = FastAPI(title="FoodFlow Notification Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"service": "notification-service", "status": "ok"}

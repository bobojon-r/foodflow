import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"


settings = Settings()

_producer: AIOKafkaProducer | None = None


async def _wait_for_kafka(retries: int = 10, delay: float = 5.0) -> bool:
    producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    for attempt in range(1, retries + 1):
        try:
            await producer.start()
            await producer.stop()
            return True
        except KafkaConnectionError:
            logger.warning("Waiting for Kafka... attempt %d/%d", attempt, retries)
            await asyncio.sleep(delay)
    return False


async def _process_order(order: dict) -> None:
    order_id = order["order_id"]
    total = order["total_price"]
    logger.info("Processing payment for order_id=%s amount=%s", order_id, total)
    if _producer:
        event = {"order_id": order_id, "amount": total, "status": "succeeded"}
        await _producer.send_and_wait("payment.succeeded", json.dumps(event).encode())
        logger.info("Published payment.succeeded for order_id=%s", order_id)


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
            try:
                await _process_order(msg.value)
            except Exception:
                logger.exception("Failed to process order event: %s", msg.value)
    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _producer
    ready = await _wait_for_kafka()
    if ready:
        _producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        await _producer.start()
        consumer_task = asyncio.create_task(_consume())
    else:
        logger.error("Kafka unavailable — payment service running without Kafka")
        consumer_task = None
    yield
    if consumer_task:
        consumer_task.cancel()
    if _producer:
        await _producer.stop()


app = FastAPI(title="FoodFlow Payment Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"service": "payment-service", "status": "ok"}

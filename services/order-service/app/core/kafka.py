import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None


async def start_producer(retries: int = 10, delay: float = 5.0) -> None:
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    for attempt in range(1, retries + 1):
        try:
            await _producer.start()
            logger.info("Kafka producer started")
            return
        except KafkaConnectionError as e:
            logger.warning("Kafka not ready (attempt %d/%d): %s", attempt, retries, e)
            if attempt < retries:
                await asyncio.sleep(delay)
    logger.error("Could not connect to Kafka after %d attempts — running without producer", retries)
    _producer = None


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        logger.info("Kafka producer stopped")


async def publish(topic: str, value: dict) -> None:
    if _producer is None:
        logger.warning("Kafka producer not available, skipping publish to %s", topic)
        return
    await _producer.send_and_wait(topic, value)
    logger.info("Published to %s: %s", topic, value)

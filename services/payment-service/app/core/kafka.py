import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None


async def get_producer() -> AIOKafkaProducer | None:
    return _producer


async def start_producer(retries: int = 10, delay: float = 5.0) -> None:
    global _producer
    probe = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    for attempt in range(1, retries + 1):
        try:
            await probe.start()
            await probe.stop()
            break
        except KafkaConnectionError:
            logger.warning("Waiting for Kafka... attempt %d/%d", attempt, retries)
            await asyncio.sleep(delay)
    else:
        logger.error("Kafka unavailable — payment service running without Kafka")
        return

    _producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    await _producer.start()
    logger.info("Kafka producer started")


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish(topic: str, payload: dict) -> None:
    if _producer is None:
        logger.warning("Kafka producer not ready — skipping publish to %s", topic)
        return
    await _producer.send_and_wait(topic, json.dumps(payload).encode())
    logger.info("Published to %s: %s", topic, payload)

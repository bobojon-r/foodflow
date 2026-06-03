import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.observability import setup_observability

if TYPE_CHECKING:
    from aiogram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOPICS = ["order.created", "order.status_changed", "payment.succeeded"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    TELEGRAM_BOT_TOKEN: str = ""


settings = Settings()


def _format_message(topic: str, value: dict) -> str:
    if topic == "order.created":
        return (
            f"🆕 Новый заказ #{value.get('order_id')}\n"
            f"Сумма: {value.get('total_price')} ₽"
        )
    if topic == "order.status_changed":
        return (
            f"📦 Заказ #{value.get('order_id')}\n"
            f"Статус: {value.get('old_status')} → {value.get('new_status')}"
        )
    if topic == "payment.succeeded":
        return (
            f"✅ Оплата прошла для заказа #{value.get('order_id')}\n"
            f"Сумма: {value.get('amount')} ₽"
        )
    return f"[{topic}] {value}"


async def _consume(bot: "Bot | None") -> None:
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
                text = _format_message(msg.topic, msg.value)
                logger.info("[NOTIFY] %s", text.replace("\n", " | "))

                if bot is not None:
                    from app.bot.notifier import broadcast
                    from app.bot.router import get_subscribers
                    await broadcast(bot, get_subscribers(), text)
            except Exception:
                logger.exception("Failed to handle event: topic=%s", msg.topic)
    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    bot = None
    bot_task = None

    if settings.TELEGRAM_BOT_TOKEN:
        from aiogram import Bot, Dispatcher
        from app.bot.router import router as bot_router

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        dp = Dispatcher()
        dp.include_router(bot_router)
        bot_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Telegram bot started (polling mode)")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")

    kafka_task = asyncio.create_task(_consume(bot))
    yield

    kafka_task.cancel()
    if bot_task:
        bot_task.cancel()
    if bot:
        await bot.session.close()


app = FastAPI(title="FoodFlow Notification Service", version="0.1.0", lifespan=lifespan)
setup_observability(app, "notification-service")


@app.get("/health")
async def health() -> dict:
    return {"service": "notification-service", "status": "ok"}

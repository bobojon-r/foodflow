import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()

# In-memory subscriber registry: maps chat_id to True.
# In production this would be persisted in a database.
_subscribers: set[int] = set()


def get_subscribers() -> set[int]:
    return _subscribers


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id not in _subscribers:
        _subscribers.add(chat_id)
        logger.info("New Telegram subscriber: chat_id=%d", chat_id)
        await message.answer(
            "Привет! Ты подписан на уведомления FoodFlow 🍕\n"
            "Буду присылать статус заказов и подтверждения оплаты."
        )
    else:
        await message.answer("Ты уже подписан на уведомления ✅")

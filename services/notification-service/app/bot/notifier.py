import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)


async def broadcast(bot: "Bot", subscribers: set[int], text: str) -> None:
    """Send text to every registered Telegram subscriber."""
    for chat_id in subscribers:
        try:
            await bot.send_message(chat_id, text)
        except Exception:
            logger.exception("Failed to send Telegram message to chat_id=%d", chat_id)

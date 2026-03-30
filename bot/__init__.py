"""Bot package initialization."""

from bot.core.bot import bot_client
from bot.core.userbot import userbot_clients
from bot.core.call import call_manager
from bot.utils.database import db
from bot.utils.cache import redis_client

__all__ = [
    "bot_client",
    "userbot_clients", 
    "call_manager",
    "db",
    "redis_client",
]

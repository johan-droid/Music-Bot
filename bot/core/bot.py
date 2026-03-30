"""Pyrogram Bot Client initialization."""

import logging
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from config import config

logger = logging.getLogger(__name__)

# Global bot client instance
bot_client = Client(
    "musicbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workdir="./sessions",
)


async def init_bot():
    """Initialize and start the bot client.
    
    Auto-loads all plugins from bot/plugins/ directory.
    """
    # Start the bot (this blocks until stopped)
    await bot_client.start()
    
    bot_info = await bot_client.get_me()
    logger.info(f"Bot started: @{bot_info.username}")
    
    # Keep running
    await bot_client.idle()
    
    return bot_client

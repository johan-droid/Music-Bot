"""
Music Bot - Telegram Voice Chat Music Bot
A Python-based bot for streaming high-quality audio into Telegram group voice calls.
"""

import asyncio
import logging
from bot.core.bot import init_bot
from bot.core.userbot import init_userbots
from bot.core.call import init_calls
from bot.core.queue import init_queue_manager
from bot.utils.database import init_database
from bot.utils.cache import init_redis
from bot.utils.logger import setup_logging
from bot.utils.scheduler import start_scheduler
from config import config


async def main():
    """Main entry point - initialize all components."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Music Bot...")
    
    try:
        # Initialize database connections
        await init_database()
        logger.info("Database connected")
        
        await init_redis()
        logger.info("Redis connected")
        
        # Initialize queue manager
        await init_queue_manager()
        logger.info("Queue manager initialized")
        
        # Initialize userbots first (needed for calls)
        userbots = await init_userbots()
        logger.info(f"Initialized {len(userbots)} userbot(s)")
        
        # Initialize py-tgcalls
        await init_calls(userbots)
        logger.info("Call manager initialized")
        
        # Start cleanup scheduler
        start_scheduler()
        logger.info("Cleanup scheduler started")
        
        # Initialize bot client (this will block)
        bot = await init_bot()
        logger.info("Bot started successfully")
        
    except Exception as e:
        logger.exception("Failed to start bot")
        raise


if __name__ == "__main__":
    asyncio.run(main())

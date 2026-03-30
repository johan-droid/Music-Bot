"""Userbot Client(s) initialization for voice chat streaming."""

import logging
from typing import List
from pyrogram import Client
from config import config

logger = logging.getLogger(__name__)

# Global userbot clients list
userbot_clients: List[Client] = []


async def init_userbots() -> List[Client]:
    """Initialize all configured userbot clients.
    
    Returns:
        List of started Client instances
    """
    global userbot_clients
    
    sessions = config.session_strings
    
    for i, session in enumerate(sessions, 1):
        try:
            client = Client(
                f"userbot_{i}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session,
                workdir="./sessions",
            )
            
            await client.start()
            user_info = await client.get_me()
            logger.info(f"Userbot {i} started: @{user_info.username or user_info.id}")
            userbot_clients.append(client)
            
        except Exception as e:
            logger.error(f"Failed to start userbot {i}: {e}")
            if i == 1:
                # First userbot is required
                raise RuntimeError(f"Required userbot 1 failed to start: {e}")
    
    if not userbot_clients:
        raise RuntimeError("No userbots could be started")
    
    return userbot_clients


def get_available_userbot() -> Client:
    """Get a userbot using round-robin distribution.
    
    TODO: Implement active VC tracking for smarter distribution.
    
    Returns:
        Client instance
    """
    # Simple round-robin for now
    # In production, track active VC count per userbot
    if not userbot_clients:
        raise RuntimeError("No userbots available")
    
    # For now, return the first one
    # Multi-assistant scaling will be implemented in Phase 4
    return userbot_clients[0]

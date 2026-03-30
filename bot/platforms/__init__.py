"""Platform detection and routing."""

import logging
import re
from typing import Optional, Dict, Any
from pyrogram.types import Message

from bot.platforms.youtube import extract_youtube, search_youtube
from bot.platforms.spotify import extract_spotify
from bot.platforms.soundcloud import extract_soundcloud
from bot.platforms.jiosaavn import extract_jiosaavn
from bot.platforms.telegram import extract_telegram_audio

logger = logging.getLogger(__name__)


# URL patterns for platform detection
URL_PATTERNS = {
    "youtube": [
        r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)",
    ],
    "spotify": [
        r"(?:https?://)?(?:open\.)?spotify\.com",
        r"spotify:",
    ],
    "soundcloud": [
        r"(?:https?://)?(?:www\.)?soundcloud\.com",
    ],
    "jiosaavn": [
        r"(?:https?://)?(?:www\.)?jiosaavn\.com",
        r"(?:https?://)?(?:www\.)?saavn\.com",
    ],
}


def detect_platform(query: str) -> str:
    """Detect platform from URL or query.
    
    Args:
        query: URL or search query
        
    Returns:
        Platform name: youtube, spotify, soundcloud, jiosaavn, or search
    """
    for platform, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return platform
    
    return "search"


async def extract_audio(query: str, message: Message = None) -> Optional[Dict[str, Any]]:
    """Extract audio from any supported platform.
    
    Args:
        query: URL or search terms
        message: Optional Telegram message (for file extraction)
        
    Returns:
        Dict with audio URL and metadata, or None
    """
    # First check if it's a Telegram audio file reply
    if message and message.reply_to_message:
        reply = message.reply_to_message
        tg_audio = await extract_telegram_audio(reply)
        if tg_audio:
            return tg_audio
    
    # Detect platform and extract
    platform = detect_platform(query)
    
    try:
        if platform == "youtube":
            return await extract_youtube(query)
        
        elif platform == "spotify":
            return await extract_spotify(query)
        
        elif platform == "soundcloud":
            return await extract_soundcloud(query)
        
        elif platform == "jiosaavn":
            return await extract_jiosaavn(query)
        
        else:
            # Search on YouTube
            return await extract_youtube(query)
            
    except Exception as e:
        logger.error(f"Platform extraction failed: {e}")
        return None


async def search_tracks(query: str, platform: str = "auto", limit: int = 5) -> list:
    """Search tracks on specified platform.
    
    Args:
        query: Search terms
        platform: Platform to search, or "auto" for all
        limit: Max results
        
    Returns:
        List of result dicts
    """
    if platform == "auto":
        platform = "youtube"
    
    try:
        if platform == "youtube":
            return await search_youtube(query, limit)
        
        elif platform == "spotify":
            from bot.platforms.spotify import search_spotify
            return await search_spotify(query, limit)
        
        elif platform == "jiosaavn":
            from bot.platforms.jiosaavn import search_jiosaavn
            return await search_jiosaavn(query, limit)
        
        else:
            return await search_youtube(query, limit)
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


__all__ = [
    "detect_platform",
    "extract_audio",
    "search_tracks",
]

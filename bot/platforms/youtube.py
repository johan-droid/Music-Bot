"""YouTube audio extraction using yt-dlp - optimized for high-quality audio streaming."""

import logging
import asyncio
import yt_dlp
from typing import Optional, Dict, Any
from config import config

logger = logging.getLogger(__name__)

# High-quality audio format selection for Telegram 2025
# Priority: Opus > AAC 256k+ > MP3 320k > best available
YTDL_FORMAT = """
    bestaudio[ext=opus][abr>=192]/
    bestaudio[ext=webm][abr>=192]/
    bestaudio[ext=m4a][abr>=256]/
    bestaudio[ext=m4a][abr>=192]/
    bestaudio[ext=mp3][abr>=320]/
    bestaudio[ext=mp3][abr>=256]/
    bestaudio[ext=mp3][abr>=192]/
    bestaudio[ext=flac]/
    bestaudio[ext=wav]/
    bestaudio
""".replace("\n", "").replace(" ", "")

# yt-dlp options optimized for high-quality audio streaming
YTDL_OPTIONS = {
    "format": YTDL_FORMAT,
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "concurrent_fragments": 8,  # Increased for faster extraction
    "retries": 10,
    "geo_bypass": True,
    "prefer_ffmpeg": True,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "best",
        "preferredquality": "0",  # Best quality
    }],
    "extractor_args": {
        "youtube": {
            "player_skip": ["webpage", "js"],  # Skip unnecessary data
            "player_client": ["web"],
        }
    }
}

# Add cookie file if exists
import os
if os.path.exists("./cookies.txt"):
    YTDL_OPTIONS["cookiefile"] = "./cookies.txt"


class YouTubeExtractor:
    """Extracts audio stream URLs and metadata from YouTube."""
    
    def __init__(self):
        self.ydl_opts = YTDL_OPTIONS.copy()
    
    async def extract(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract audio from YouTube URL or search query.
        
        Args:
            query: YouTube URL or search terms
            
        Returns:
            Dict with url, title, duration, thumbnail or None if failed
        """
        try:
            # Run yt-dlp in thread pool to not block
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._extract_sync, query)
        except Exception as e:
            logger.error(f"YouTube extraction failed: {e}")
            return None
    
    def _extract_sync(self, query: str) -> Optional[Dict[str, Any]]:
        """Synchronous extraction using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Check if it's a URL or search
                if not query.startswith(("http://", "https://", "www.", "youtube.com", "youtu.be")):
                    # Search query
                    query = f"ytsearch:{query}"
                
                info = ydl.extract_info(query, download=False)
                
                # Handle search results
                if "entries" in info:
                    if not info["entries"]:
                        return None
                    info = info["entries"][0]
                
                # Get best audio format
                formats = info.get("formats", [])
                audio_url = None
                
                # Prefer m4a, then webm, then any best audio
                for fmt in formats:
                    if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                        audio_url = fmt.get("url")
                        break
                
                # Fallback to any format with audio
                if not audio_url:
                    for fmt in formats:
                        if fmt.get("acodec") != "none":
                            audio_url = fmt.get("url")
                            break
                
                if not audio_url:
                    return None
                
                return {
                    "url": audio_url,
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "source": "youtube",
                }
                
        except Exception as e:
            logger.error(f"yt-dlp extraction error: {e}")
            return None
    
    async def search(self, query: str, limit: int = 5) -> list:
        """Search YouTube and return multiple results.
        
        Args:
            query: Search terms
            limit: Max results to return
            
        Returns:
            List of result dicts
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._search_sync, query, limit)
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []
    
    def _search_sync(self, query: str, limit: int) -> list:
        """Synchronous search."""
        opts = self.ydl_opts.copy()
        opts["playlist_items"] = f"1-{limit}"
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                search_query = f"ytsearch{limit}:{query}"
                info = ydl.extract_info(search_query, download=False)
                
                results = []
                if "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            results.append({
                                "title": entry.get("title", "Unknown"),
                                "duration": entry.get("duration", 0),
                                "thumbnail": entry.get("thumbnail"),
                                "uploader": entry.get("uploader"),
                                "id": entry.get("id"),
                                "url": f"https://youtube.com/watch?v={entry.get('id')}",
                            })
                return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []


# Global extractor instance
youtube = YouTubeExtractor()


async def extract_youtube(query: str) -> Optional[Dict[str, Any]]:
    """Convenience function to extract from YouTube."""
    return await youtube.extract(query)


async def search_youtube(query: str, limit: int = 5) -> list:
    """Convenience function to search YouTube."""
    return await youtube.search(query, limit)

"""SoundCloud integration via yt-dlp."""

import logging
from typing import Optional, Dict, Any
from bot.platforms.youtube import youtube

logger = logging.getLogger(__name__)


class SoundCloudExtractor:
    """Extract audio from SoundCloud URLs using yt-dlp."""
    
    def __init__(self):
        # yt-dlp has native SoundCloud support
        pass
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract audio from SoundCloud URL.
        
        Args:
            url: SoundCloud track URL
            
        Returns:
            Dict with audio URL and metadata
        """
        # Use yt-dlp which has native SoundCloud support
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._extract_sync, url)
        except Exception as e:
            logger.error(f"SoundCloud extraction failed: {e}")
            return None
    
    def _extract_sync(self, url: str) -> Optional[Dict[str, Any]]:
        """Synchronous extraction."""
        import yt_dlp
        
        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get audio URL
                audio_url = None
                if "url" in info:
                    audio_url = info["url"]
                elif "formats" in info:
                    for fmt in info["formats"]:
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
                    "source": "soundcloud",
                }
                
        except Exception as e:
            logger.error(f"SoundCloud extraction error: {e}")
            return None


# Global extractor
soundcloud = SoundCloudExtractor()


async def extract_soundcloud(url: str) -> Optional[Dict[str, Any]]:
    """Extract from SoundCloud URL."""
    return await soundcloud.extract(url)

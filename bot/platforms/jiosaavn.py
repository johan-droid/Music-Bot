"""JioSaavn integration for Indian music."""

import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# JioSaavn API endpoints
JIOSAAVN_API = "https://www.jiosaavn.com/api.php"


class JioSaavnExtractor:
    """Extract audio from JioSaavn using their API."""
    
    def __init__(self):
        self.session: aiohttp.ClientSession = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def extract(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract audio from JioSaavn URL or search.
        
        Args:
            query: JioSaavn URL or search terms
            
        Returns:
            Dict with audio URL and metadata
        """
        try:
            if "jiosaavn.com" in query or "saavn.com" in query:
                # Extract from URL
                return await self._extract_from_url(query)
            else:
                # Search and extract first result
                results = await self.search(query, limit=1)
                if results:
                    return await self._extract_from_url(results[0]["url"])
                return None
        except Exception as e:
            logger.error(f"JioSaavn extraction failed: {e}")
            return None
    
    async def _extract_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract track info from JioSaavn URL."""
        try:
            # Extract song ID from URL
            import re
            match = re.search(r'/(song|album)/[^/]+/([^/]+)', url)
            if not match:
                return None
            
            song_id = match.group(2)
            
            # Call JioSaavn API
            session = await self._get_session()
            
            params = {
                "__call": "song.getDetails",
                "pids": song_id,
                "api_version": "4",
                "_format": "json",
                "_marker": "0",
            }
            
            async with session.get(JIOSAAVN_API, params=params) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if "songs" not in data or not data["songs"]:
                    return None
                
                song = data["songs"][0]
                
                # Get best quality audio URL
                media_url = song.get("media_preview_url", "")
                # Upgrade to full quality
                media_url = media_url.replace("preview", "aac")
                
                # Try to get 320kbps
                high_quality = media_url.replace("_96_p.mp4", "_320.mp4")
                
                return {
                    "url": high_quality or media_url,
                    "title": song.get("song", "Unknown"),
                    "duration": int(song.get("duration", 0)),
                    "thumbnail": song.get("image", song.get("og_image")),
                    "artists": song.get("primary_artists", "Unknown"),
                    "source": "jiosaavn",
                }
                
        except Exception as e:
            logger.error(f"JioSaavn URL extraction error: {e}")
            return None
    
    async def search(self, query: str, limit: int = 5) -> list:
        """Search JioSaavn.
        
        Args:
            query: Search terms
            limit: Max results
            
        Returns:
            List of result dicts
        """
        try:
            session = await self._get_session()
            
            params = {
                "__call": "search.getResults",
                "q": query,
                "n": limit,
                "api_version": "4",
                "_format": "json",
                "_marker": "0",
            }
            
            async with session.get(JIOSAAVN_API, params=params) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                results = []
                for song in data.get("results", []):
                    results.append({
                        "title": song.get("title", "Unknown"),
                        "duration": int(song.get("duration", 0)),
                        "thumbnail": song.get("image"),
                        "artists": song.get("primary_artists", "Unknown"),
                        "url": f"https://www.jiosaavn.com/song/{song.get('perma_url', '')}",
                        "source": "jiosaavn",
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"JioSaavn search error: {e}")
            return []


# Global extractor
jiosaavn = JioSaavnExtractor()


async def extract_jiosaavn(query: str) -> Optional[Dict[str, Any]]:
    """Extract from JioSaavn."""
    return await jiosaavn.extract(query)


async def search_jiosaavn(query: str, limit: int = 5) -> list:
    """Search JioSaavn."""
    return await jiosaavn.search(query, limit)

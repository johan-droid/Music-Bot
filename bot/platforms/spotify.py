"""Spotify integration - metadata fetch with YouTube resolution."""

import logging
from typing import Optional, Dict, Any
from bot.platforms.youtube import extract_youtube, search_youtube
from config import config

logger = logging.getLogger(__name__)

# Try to import spotipy, fallback to None if not available
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    logger.warning("spotipy not installed, Spotify features limited")


class SpotifyExtractor:
    """Extract Spotify metadata and resolve to YouTube audio."""
    
    def __init__(self):
        self.sp = None
        if SPOTIPY_AVAILABLE and config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
            try:
                auth = SpotifyClientCredentials(
                    client_id=config.SPOTIFY_CLIENT_ID,
                    client_secret=config.SPOTIFY_CLIENT_SECRET
                )
                self.sp = spotipy.Spotify(auth_manager=auth)
                logger.info("Spotify client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Spotify: {e}")
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract track info from Spotify URL and resolve to YouTube audio.
        
        Args:
            url: Spotify track/album/playlist URL
            
        Returns:
            Dict with audio URL and metadata, or None
        """
        if not self.sp:
            logger.warning("Spotify client not available")
            return None
        
        try:
            # Parse URL to get track ID
            track_id = self._extract_track_id(url)
            if not track_id:
                return None
            
            # Get track info
            track = self.sp.track(track_id)
            
            # Build search query
            artists = ", ".join([a["name"] for a in track["artists"]])
            title = track["name"]
            search_query = f"{artists} - {title}"
            
            # Get thumbnail
            thumbnail = None
            if track["album"]["images"]:
                thumbnail = track["album"]["images"][0]["url"]
            
            # Search on YouTube
            yt_result = await extract_youtube(search_query)
            
            if yt_result:
                yt_result["title"] = f"{title} - {artists}"
                yt_result["thumbnail"] = thumbnail or yt_result.get("thumbnail")
                yt_result["source"] = "spotify"
                yt_result["spotify_url"] = url
                return yt_result
            
            return None
            
        except Exception as e:
            logger.error(f"Spotify extraction failed: {e}")
            return None
    
    def _extract_track_id(self, url: str) -> Optional[str]:
        """Extract track ID from Spotify URL."""
        import re
        
        # Handle various Spotify URL formats
        patterns = [
            r"spotify:track:([a-zA-Z0-9]+)",
            r"open\.spotify\.com/track/([a-zA-Z0-9]+)",
            r"spotify\.com/track/([a-zA-Z0-9]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def search(self, query: str, limit: int = 5) -> list:
        """Search Spotify tracks and return results with YouTube resolution.
        
        Args:
            query: Search terms
            limit: Max results
            
        Returns:
            List of track dicts
        """
        if not self.sp:
            # Fallback to YouTube search
            return await search_youtube(query, limit)
        
        try:
            results = self.sp.search(q=query, type="track", limit=limit)
            tracks = results.get("tracks", {}).get("items", [])
            
            formatted = []
            for track in tracks:
                artists = ", ".join([a["name"] for a in track["artists"]])
                thumbnail = track["album"]["images"][0]["url"] if track["album"]["images"] else None
                
                formatted.append({
                    "title": track["name"],
                    "artists": artists,
                    "duration": track["duration_ms"] // 1000,
                    "thumbnail": thumbnail,
                    "url": track["external_urls"]["spotify"],
                    "source": "spotify",
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Spotify search failed: {e}")
            return await search_youtube(query, limit)


# Global extractor
spotify = SpotifyExtractor()


async def extract_spotify(url: str) -> Optional[Dict[str, Any]]:
    """Extract from Spotify URL."""
    return await spotify.extract(url)


async def search_spotify(query: str, limit: int = 5) -> list:
    """Search Spotify."""
    return await spotify.search(query, limit)

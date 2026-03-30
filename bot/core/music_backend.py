"""
Legal Music Extraction Backend - Free Tier Compatible
Supports: JioSaavn, YouTube (fair use), SoundCloud
"""

import asyncio
import logging
import aiohttp
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Universal track representation."""
    title: str
    artist: str
    duration: int  # seconds
    stream_url: str
    thumbnail: Optional[str] = None
    source: str = "unknown"  # jiosaavn, youtube, soundcloud
    track_id: Optional[str] = None


class JioSaavnExtractor:
    """
    JioSaavn extractor - Legal free music source (Indian music).
    No API key required, public endpoints.
    """
    
    BASE_URL = "https://www.jiosaavn.com/api.php"
    
    async def search(self, query: str, limit: int = 5) -> List[Track]:
        """Search for songs on JioSaavn."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "_format": "json",
                    "_marker": "0",
                    "api_version": "4",
                    "ctx": "web6dot0",
                    "q": query,
                    "n": limit,
                    "p": "1",
                    "caller": "PWA",
                    "saavn_app": "2",
                    "__call": "search.getResults"
                }
                
                async with session.get(self.BASE_URL, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    results = []
                    
                    for song in data.get("results", []):
                        track = Track(
                            title=song.get("title", "Unknown").strip(),
                            artist=song.get("primary_artists", "Unknown").strip(),
                            duration=int(song.get("duration", 0)),
                            stream_url="",  # Will be resolved when played
                            thumbnail=song.get("image", "").replace("150x150", "500x500"),
                            source="jiosaavn",
                            track_id=song.get("id")
                        )
                        results.append(track)
                    
                    return results
                    
        except Exception as e:
            logger.error(f"JioSaavn search error: {e}")
            return []
    
    async def get_stream_url(self, track_id: str) -> Optional[str]:
        """Get streaming URL for a track."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "_format": "json",
                    "_marker": "0",
                    "api_version": "4",
                    "ctx": "web6dot0",
                    "caller": "PWA",
                    "saavn_app": "2",
                    "__call": "song.getDetails",
                    "pids": track_id
                }
                
                async with session.get(self.BASE_URL, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    songs = data.get("songs", [])
                    if not songs:
                        return None
                    
                    # Get the highest quality URL
                    media_url = songs[0].get("media_url", "")
                    if media_url:
                        # Upgrade to 320kbps if available
                        return media_url.replace("_96.", "_320.").replace("_160.", "_320.")
                    
                    return media_url
                    
        except Exception as e:
            logger.error(f"JioSaavn stream error: {e}")
            return None


class MusicBackend:
    """
    Unified music backend that tries multiple sources.
    Priority: JioSaavn (legal) → YouTube (fair use) → SoundCloud
    """
    
    def __init__(self):
        self.jiosaavn = JioSaavnExtractor()
        # YouTube and SoundCloud extractors are already in bot/platforms/
        from bot.platforms.youtube import youtube
        from bot.platforms.soundcloud import soundcloud
        self.youtube = youtube
        self.soundcloud = soundcloud
    
    async def search(self, query: str, limit: int = 5) -> List[Track]:
        """
        Search across all sources.
        Returns unified Track objects.
        """
        tracks = []
        
        # Try JioSaavn first (legal, no copyright issues for Indian music)
        try:
            jio_tracks = await self.jiosaavn.search(query, limit)
            tracks.extend(jio_tracks)
            logger.info(f"JioSaavn found {len(jio_tracks)} tracks")
        except Exception as e:
            logger.warning(f"JioSaavn search failed: {e}")
        
        # Try YouTube for broader catalog
        if len(tracks) < limit:
            try:
                yt_results = await self.youtube.search(query, limit - len(tracks))
                for result in yt_results:
                    track = Track(
                        title=result.get("title", "Unknown"),
                        artist=result.get("uploader", "Unknown"),
                        duration=result.get("duration", 0),
                        stream_url=result.get("url", ""),
                        thumbnail=result.get("thumbnail"),
                        source="youtube",
                        track_id=result.get("id")
                    )
                    tracks.append(track)
                logger.info(f"YouTube found {len(yt_results)} tracks")
            except Exception as e:
                logger.warning(f"YouTube search failed: {e}")
        
        # Try SoundCloud as final fallback
        if len(tracks) < limit:
            try:
                sc_results = await self.soundcloud.search(query, limit - len(tracks))
                for result in sc_results:
                    track = Track(
                        title=result.get("title", "Unknown"),
                        artist=result.get("artist", "Unknown"),
                        duration=result.get("duration", 0),
                        stream_url=result.get("stream_url", ""),
                        thumbnail=result.get("thumbnail"),
                        source="soundcloud",
                        track_id=result.get("id")
                    )
                    tracks.append(track)
                logger.info(f"SoundCloud found {len(sc_results)} tracks")
            except Exception as e:
                logger.warning(f"SoundCloud search failed: {e}")
        
        return tracks[:limit]
    
    async def get_stream_url(self, track: Track) -> Optional[str]:
        """Resolve stream URL for a track based on its source."""
        if track.source == "jiosaavn":
            return await self.jiosaavn.get_stream_url(track.track_id)
        elif track.source == "youtube":
            result = await self.youtube.extract(track.track_id or track.stream_url)
            return result.get("url") if result else None
        elif track.source == "soundcloud":
            return track.stream_url if track.stream_url else None
        return None


# Global instance
music_backend = MusicBackend()

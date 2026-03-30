from pydantic_settings import BaseSettings
from typing import Optional, List


class Config(BaseSettings):
    """Bot configuration loaded from environment variables."""
    
    # Telegram API mode (set FALSE to run without Telegram client auth)
    TELEGRAM_ENABLED: bool = True

    # Telegram API credentials (from my.telegram.org)
    # Required only when TELEGRAM_ENABLED=true
    API_ID: Optional[int] = None
    API_HASH: Optional[str] = None
    
    # Bot token from @BotFather
    BOT_TOKEN: Optional[str] = None
    
    # Owner user ID
    OWNER_ID: Optional[int] = None
    
    # Userbot session strings (1 required when TELEGRAM_ENABLED=true)
    SESSION_STRING_1: Optional[str] = None
    SESSION_STRING_2: Optional[str] = None
    SESSION_STRING_3: Optional[str] = None
    SESSION_STRING_4: Optional[str] = None
    SESSION_STRING_5: Optional[str] = None
    
    # MongoDB
    MONGO_URI: str = "mongodb://mongo:27017/musicbot"
    
    # Redis (optional - falls back to SQLite if not configured)
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    # SQLite cache path (used when Redis is not available)
    SQLITE_CACHE_PATH: str = "./data/cache.db"
    
    # Supabase (alternative to MongoDB)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    
    # Spotify (optional)
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None
    
    # Genius (optional - for lyrics)
    GENIUS_TOKEN: Optional[str] = None
    
    # Log group/channel ID (optional)
    LOG_GROUP_ID: Optional[int] = None
    
    # Bot behavior settings
    MAX_QUEUE_SIZE: int = 100
    DEFAULT_VOLUME: int = 100
    COMMAND_COOLDOWN: int = 3  # seconds
    
    # Audio quality settings (Telegram 2025 optimized)
    AUDIO_QUALITY: str = "high"  # standard, high, premium, lossless
    AUDIO_BITRATE: int = 192  # kbps (128-320)
    AUDIO_LOUDNORM: bool = True  # EBU R128 loudness normalization
    
    @property
    def session_strings(self) -> List[str]:
        """Return list of valid session strings."""
        sessions = [self.SESSION_STRING_1]
        for s in [self.SESSION_STRING_2, self.SESSION_STRING_3, 
                  self.SESSION_STRING_4, self.SESSION_STRING_5]:
            if s:
                sessions.append(s)
        return sessions
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
config = Config()

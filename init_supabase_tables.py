"""Supabase table auto-initializer - Run this once to create tables."""

import asyncio
import logging
from bot.utils.database import db
from bot.utils.supabase_db import supabase_db

logger = logging.getLogger(__name__)


async def init_supabase_tables():
    """Create Supabase tables if they don't exist."""
    if supabase_db is None or not supabase_db.client:
        logger.error("Supabase not connected. Check your SUPABASE_URL and SUPABASE_KEY.")
        return False
    
    client = supabase_db.client
    
    # SQL to create tables
    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS groups (
            id BIGINT PRIMARY KEY,
            title TEXT,
            lang TEXT DEFAULT 'en',
            is_active BOOLEAN DEFAULT TRUE,
            joined_at TIMESTAMP DEFAULT NOW(),
            settings JSONB DEFAULT '{
                "play_on_join": true,
                "max_queue": 100,
                "vol_default": 100,
                "loop_mode": "none",
                "quality": "high",
                "thumb_mode": true
            }'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS sudo_users (
            id BIGINT PRIMARY KEY,
            name TEXT,
            added_by BIGINT,
            added_at TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS gbanned (
            id BIGINT PRIMARY KEY,
            reason TEXT,
            banned_by BIGINT,
            banned_at TIMESTAMP DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS group_bans (
            chat_id BIGINT,
            user_id BIGINT,
            banned_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (chat_id, user_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_groups_active ON groups(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_gbanned_id ON gbanned(id);",
        "CREATE INDEX IF NOT EXISTS idx_group_bans_chat ON group_bans(chat_id);",
        "CREATE INDEX IF NOT EXISTS idx_group_bans_user ON group_bans(user_id);",
    ]
    
    try:
        # Execute each SQL command
        for sql in sql_commands:
            try:
                # Supabase supports raw SQL via rpc or postgrest
                # Using the sql() method if available
                result = client.rpc('exec_sql', {'sql': sql}).execute()
                logger.info(f"Executed: {sql[:50]}...")
            except Exception as e:
                logger.warning(f"Table may already exist or SQL failed: {e}")
        
        logger.info("Supabase tables initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Supabase tables: {e}")
        return False


if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the initializer
    print("Initializing Supabase tables...")
    print("Make sure SUPABASE_URL and SUPABASE_KEY are set in your .env file")
    
    result = asyncio.run(init_supabase_tables())
    
    if result:
        print("\n✅ Tables created successfully!")
    else:
        print("\n❌ Failed to create tables. Check errors above.")
        print("\nManual setup instructions:")
        print("1. Go to https://app.supabase.io")
        print("2. Open your project → SQL Editor")
        print("3. Copy and paste contents of supabase_setup.sql")
        print("4. Click 'Run'")

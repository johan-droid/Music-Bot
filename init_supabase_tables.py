"""Supabase table auto-initializer - Run this once to create tables."""

import os
import sys
import asyncio
from pathlib import Path

# Load .env using python-dotenv (installed in requirements)
try:
    from dotenv import load_dotenv
    
    # Check for .env files - prioritize bot/ subdirectory first
    env_paths = [
        Path(__file__).parent / "bot" / ".env.local",
        Path(__file__).parent / "bot" / ".env",
        Path(__file__).parent / ".env.local",
        Path(__file__).parent / ".env",
    ]
    loaded = False
    
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded env from: {env_path}")
            loaded = True
            break
    
    if not loaded:
        print(f"⚠️  No .env or .env.local file found")
        print("   Looking for environment variables...")
        
except ImportError:
    print("⚠️  python-dotenv not installed, using manual parsing")
    # Fallback manual parsing
    env_paths = [
        Path(__file__).parent / "bot" / ".env.local",
        Path(__file__).parent / "bot" / ".env",
        Path(__file__).parent / ".env.local",
        Path(__file__).parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if value:
                            os.environ[key] = value
            print(f"✅ Loaded env from: {env_path}")
            break


async def init_supabase_tables():
    """Create Supabase tables if they don't exist."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Debug: Show what we found (masked)
    if url:
        print(f"   Found SUPABASE_URL: {url[:20]}...")
    else:
        print("   SUPABASE_URL: NOT FOUND")
    
    if key:
        print(f"   Found SUPABASE_KEY: {key[:10]}...{key[-5:]}")
    else:
        print("   SUPABASE_KEY: NOT FOUND")
    
    if not url or not key:
        print("\n❌ Error: SUPABASE_URL and SUPABASE_KEY not found")
        print("\nAdd these to your .env file:")
        print("SUPABASE_URL=https://your-project.supabase.co")
        print("SUPABASE_KEY=your-service-role-key")
        return False
    
    try:
        from supabase import create_client
        client = create_client(url, key)
        print(f"✅ Connected to Supabase: {url[:30]}...")
    except ImportError:
        print("❌ Error: supabase package not installed")
        print("Run: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return False
    
    # Read SQL from file
    sql_path = Path(__file__).parent / "supabase_setup.sql"
    if not sql_path.exists():
        print("❌ Error: supabase_setup.sql not found")
        return False
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print("\n⚠️  Supabase REST API cannot execute DDL (CREATE TABLE) statements.")
    print("You must create tables manually via the SQL Editor.")
    print("\n" + "="*60)
    print("📋 MANUAL SETUP INSTRUCTIONS:")
    print("="*60)
    print("1. Go to: https://app.supabase.io")
    print("2. Select your project")
    print("3. Click 'SQL Editor' in the left sidebar")
    print("4. Click 'New Query'")
    print("5. Copy ALL contents from supabase_setup.sql")
    print("6. Paste into the SQL Editor")
    print("7. Click 'Run'")
    print("="*60)
    print("\n✅ After running the SQL, your tables will be ready!")
    
    # Try to verify connection by querying
    try:
        result = client.table('groups').select('*').limit(1).execute()
        print("\n✅ Connection test passed - groups table exists!")
    except Exception as e:
        if "PGRST205" in str(e) or "not found" in str(e).lower():
            print("\n⚠️  Tables not yet created - follow instructions above")
        else:
            print(f"\n⚠️  Connection test: {e}")
    
    return True


if __name__ == "__main__":
    print("🔧 Supabase Table Initializer")
    print("="*60)
    
    result = asyncio.run(init_supabase_tables())
    
    if not result:
        sys.exit(1)

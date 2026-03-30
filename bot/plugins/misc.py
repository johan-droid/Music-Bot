"""Utility commands: /start, /help, /ping"""

import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import rate_limit
from config import config


@Client.on_message(filters.command("start") & filters.private)
@rate_limit
async def start_cmd(client: Client, message: Message):
    """Handle /start command."""
    user = message.from_user
    
    text = f"""
👋 **Hello {user.mention}!**

I'm a **Voice Chat Music Bot** that streams high-quality audio into Telegram group voice calls.

**Key Features:**
• 🎵 Stream from YouTube, Spotify, SoundCloud, JioSaavn
• 🎛 Admin-only playback control
• 📢 High-quality audio (48kHz PCM)
• 🔄 Gapless playback with prefetch
• 📋 Persistent queues per group

**Commands:**
Use /help to see all available commands.

**Note:** I work in groups only. Add me to a group and give me admin rights with "Manage Voice Chats" permission!
    """
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true")],
        [InlineKeyboardButton("📖 Help", callback_data="help")]
    ])
    
    await message.reply(text, reply_markup=buttons)


@Client.on_message(filters.command("help"))
@rate_limit
async def help_cmd(client: Client, message: Message):
    """Handle /help command."""
    
    text = f"""
📚 **Music Bot Commands**

**🎵 Playback Commands (Admin Only):**
• `/play [query/url]` - Play a song or add to queue
• `/vplay [query/url]` - Play video (video mode)
• `/pause` - Pause current playback
• `/resume` - Resume playback  
• `/skip` - Skip to next song
• `/stop` or `/end` - Stop and clear queue
• `/seek [seconds]` - Seek to position
• `/replay` - Restart current track
• `/volume [1-200]` - Adjust volume (default: 100)

**📋 Queue Commands:**
• `/queue` - Show current queue
• `/clearqueue` - Clear all songs
• `/remove [position]` - Remove specific song
• `/shuffle` - Shuffle queue

**📊 Information:**
• `/now` or `/np` - Now playing info
• `/ping` - Check bot latency

**⚙️ Admin Commands:**
• `/addsudo [user]` - Grant sudo (owner only)
• `/delsudo [user]` - Revoke sudo (owner only)
• `/sudolist` - List sudo users
• `/gban [user]` - Global ban (sudo+)
• `/ungban [user]` - Remove global ban
• `/block [user]` - Block in this group
• `/unblock [user]` - Unblock in this group
• `/stats` - Bot statistics
• `/broadcast [message]` - Broadcast to all groups
• `/restart` - Restart bot (owner only)
• `/maintenance [on/off]` - Toggle maintenance

**Supported Sources:**
• YouTube (URLs & search)
• Spotify (metadata → YT)
• SoundCloud
• JioSaavn
• Telegram audio files

**Note:** All playback commands require admin rights in the group.
    """
    
    await message.reply(text)


@Client.on_message(filters.command("ping"))
@rate_limit
async def ping_cmd(client: Client, message: Message):
    """Handle /ping command - check latency."""
    start_time = time.time()
    
    # Send initial message
    reply = await message.reply("🏓 **Pong!**")
    
    # Calculate latency
    end_time = time.time()
    latency = (end_time - start_time) * 1000
    
    # Edit with stats
    text = f"""
🏓 **Pong!**

**Latency:** `{latency:.1f}ms`
**Uptime:** Check /stats for details
    """
    
    await reply.edit(text)

"""Utility commands: /help, /ping"""

import time
import platform
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import require_admin, rate_limit
from config import config


@Client.on_message(filters.command("help") & (filters.private | filters.group))
@rate_limit
async def help_cmd(client: Client, message: Message):
    """Handle /help command - open to everyone."""

    text = """
💀 **YOHOHOHO! Welcome Aboard the Thousand Sunny!**

> *"I am Brook, the Soul King! Music is my life... even though I don't have one!"*

🎻 **Let me play you the song of my people... through this bot!**

━━━━━━━━━━━━━━━━━━━━━
� **MUSIC COMMANDS**
━━━━━━━━━━━━━━━━━━━━━
� `/play [song]` — Request a song, Yohoho!
🎬 `/vplay [video]` — Video mode *(Admin only)*
⏸ `/pause` — Pause my performance
▶️ `/resume` — Resume the concert
⏭ `/skip` — Next track, please!
⏹ `/stop` — Stop the music
⏩ `/seek [sec]` — Jump in the track
🔁 `/replay` — Play it again!
🔊 `/volume [1-200]` — Louder! LOUDER!

━━━━━━━━━━━━━━━━━━━━━
📋 **QUEUE & PLAYLIST**
━━━━━━━━━━━━━━━━━━━━━
� `/queue` — The setlist
🎧 `/now` — What's playing now?
🗑️ `/clearqueue` — Clear the stage
❌ `/remove [pos]` — Remove a song
🔀 `/shuffle` — Mix it up!
🔂 `/loop` — Loop mode *(track/queue/off)*

━━━━━━━━━━━━━━━━━━━━━
⚔️ **CREW CAPTAIN COMMANDS**
━━━━━━━━━━━━━━━━━━━━━
👑 `/addsudo` — Promote to crew member *(Owner)*
🚫 `/delsudo` — Demote
📜 `/sudolist` — Crew roster
📛 `/gban` — Banish from seas *(Sudo+)*
✅ `/ungban` — Pardon
🔒 `/block` — Block in group
📊 `/stats` — Ship's log
📢 `/broadcast` — Message all ports *(Owner)*
🔄 `/restart` — Reboot *(Owner)*

━━━━━━━━━━━━━━━━━━━━━
🌐 **SUPPORTED SOURCES**
━━━━━━━━━━━━━━━━━━━━━
🎵 YouTube • Spotify • SoundCloud
🎵 JioSaavn • Telegram Audio

━━━━━━━━━━━━━━━━━━━━━
💀 *"May I see your panties?"* — Just kidding! YOHOHOHO!
    """

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Start Playing", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📢 Support", url=f"https://t.me/{config.SUPPORT_CHAT_LINK.lstrip('@')}" if hasattr(config, 'SUPPORT_CHAT_LINK') else "https://t.me/"),
        ]
    ])

    await message.reply(text, reply_markup=buttons if hasattr(config, 'SUPPORT_CHAT_LINK') else None)


@Client.on_message(filters.command("ping") & (filters.private | filters.group))
@rate_limit
async def ping_cmd(client: Client, message: Message):
    """Check bot latency with a Brook-themed response."""
    import os
    import asyncio

    start = time.monotonic()
    reply = await message.reply("💀 *Pinging... even a skeleton can feel the beat!*")
    latency = (time.monotonic() - start) * 1000

    # Emoji quality indicator
    if latency < 100:
        quality = "🟢 Excellent"
        brook_quote = "Fast as the rhythm of my violin! YOHOHOHO!"
    elif latency < 300:
        quality = "🟡 Good"
        brook_quote = "Steady, like a soulful ballad!"
    else:
        quality = "🔴 High"
        brook_quote = "A bit slow... even my bones react faster! Yohoho!"

    # Build a mini visual bar for latency
    bar_len = min(int(latency / 30), 10)
    bar = "▰" * bar_len + "▱" * (10 - bar_len)

    text = f"""
💀 **PONG! The Soul King responds!**

⚡ **Latency:** `{latency:.1f}ms`
📊 **Signal:** `{bar}` {quality}
🐍 **Python:** `{platform.python_version()}`

💬 *\"{brook_quote}\"*
    """

    await reply.edit(text)

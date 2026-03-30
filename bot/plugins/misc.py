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
💀 **YOHOHOHO! The Soul King Presents...**

> *"Even without flesh, my music has SOUL!"*
— **Brook, Living Skeleton & Gentleman**

⚔️ **CAPTAIN'S ORDERS** *(Owner Only)*
`👑 /addsudo` — Promote to First Mate
`🚫 /delsudo` — Walk the plank
`📢 /broadcast` — Message all crews
`🔄 /restart` — Restart the ship

🦴 **CREW COMMANDS** *(All Mates Welcome)*
`🎵 /play [song]` — Request a tune, Yohoho!
`⏸ /pause` — Pause the soul
`▶️ /resume` — Resume the rhythm
`⏭ /skip` — Next melody
`⏹ /stop` — Silence the violin
`🔊 /volume` — Crank it to 11!

� **THE SETLIST** *(Queue Control)*
`� /queue` — View the playlist
`🔀 /shuffle` — Mix the tracks
`� /loop` — Repeat the magic
`�️ /clearqueue` — Clear the stage

� **SUPPORTED SOURCES**
YouTube • Spotify • SoundCloud • JioSaavn

💀 *"May your soul always find good music!"*
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

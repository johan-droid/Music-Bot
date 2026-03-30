"""Play command: /play, /vplay with smart title detection and conflict resolution."""

import re
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.permissions import rate_limit, get_permission_level
from bot.utils.formatters import format_duration, format_track_info, truncate_text
from bot.utils.thumbnails import generate_np_thumbnail
from bot.utils.title_detector import conflict_resolver, normalize_text
from bot.utils.audio_config import get_audio_optimizer, AudioQuality
from bot.platforms import extract_audio, youtube
from bot.core.queue import queue_manager
from bot.core.call import call_manager
from bot.core.bot import bot_client
from pytgcalls.types import AudioPiped, AudioParameters
from config import config

logger = logging.getLogger(__name__)

# Active now playing messages per chat
_np_messages: dict = {}

# Pending conflict resolutions
_pending_conflicts: dict = {}  # {chat_id: {user_id: {message_id, tracks, query_msg}}}


@Client.on_message(filters.command(["play", "vplay"]) & filters.group)
@rate_limit
async def play_cmd(client: Client, message: Message):
    """Handle /play command - now open to VC participants."""
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    
    if not user_id:
        return
    
    # Check permission level - allow VC participants (level 2)
    level = await get_permission_level(user_id, chat_id, check_vc=True)
    if level < 2:  # Not admin AND not in VC
        await message.reply("⛔ You need to be a voice chat participant or admin to use this command.")
        return
    
    # Check maintenance
    from bot.utils.cache import cache
    if await cache.is_maintenance() and level < 4:
        await message.reply("🔧 Bot is under maintenance.")
        return
    
    # Get query
    query = " ".join(message.command[1:]) if len(message.command) > 1 else ""
    
    # Check for reply with audio
    if not query and message.reply_to_message:
        reply = message.reply_to_message
        if reply.audio or reply.voice or reply.video:
            # Handle audio file reply
            from bot.platforms.telegram import TelegramAudioHandler
            handler = TelegramAudioHandler()
            track = await handler.extract_from_message(reply)
            if track:
                await add_track_and_play(message, chat_id, user_id, track, search_msg=None)
                return
    elif not query:
        await message.reply("❌ Please provide a song name or URL.\nUsage: `/play <query or URL>`")
        return
    
    # Check if it's a direct URL
    url_patterns = [
        r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/.+$',
        r'^(https?://)?(open\.)?spotify\.com/.+$',
        r'^(https?://)?(soundcloud|snd)\.sc/.+$',
        r'^(https?://)?music\.apple\.com/.+$',
        r'^(https?://)?deezer\.page\.link/.+$',
        r'^(https?://)?www\.jiosaavn\.com/.+$',
        r'^(https?://)?open\.jiosaavn\.com/.+$',
    ]
    
    is_url = any(re.match(pattern, query, re.IGNORECASE) for pattern in url_patterns)
    
    # Send searching message
    search_msg = await message.reply("🔍 Searching with smart title detection...")
    
    try:
        if is_url:
            # Direct URL - extract normally
            track = await extract_audio(query, message)
            if not track:
                await search_msg.edit("❌ Could not extract audio from URL.")
                return
            await add_track_and_play(message, chat_id, user_id, track, search_msg)
        else:
            # Search with conflict detection
            result = await conflict_resolver.search_with_conflicts(
                query,
                lambda q: youtube.YouTubeExtractor().search(q, max_results=5),
                max_results=5
            )
            
            if result['status'] == 'not_found':
                await search_msg.edit(result['message'])
                return
            
            if result['status'] == 'conflict':
                # Show conflict resolution options
                await show_conflict_options(message, chat_id, user_id, result['conflicts'], search_msg)
                return
            
            # Single result - add to queue
            track = result['selected']
            await add_track_and_play(message, chat_id, user_id, track, search_msg)
            
    except Exception as e:
        logger.exception("Play command failed")
        await search_msg.edit(f"❌ Error: {str(e)}")


async def start_playback(chat_id: int):
    """Start or continue playback for a chat with optimized audio quality."""
    try:
        # Get next track
        track = await queue_manager.get_next(chat_id)
        if not track:
            await queue_manager.set_status(chat_id, "idle")
            return
        
        # Set playing status
        await queue_manager.set_status(chat_id, "playing")
        
        # Get optimized audio configuration
        optimizer = get_audio_optimizer()
        ffmpeg_params = optimizer.get_ffmpeg_params(track["url"])
        
        # Check if already in call
        is_active = chat_id in call_manager.active_chats
        
        # Create high-quality AudioPiped with optimized parameters
        audio = AudioPiped(
            track["url"],
            audio_parameters=ffmpeg_params["audio_parameters"],
            ffmpeg_parameters=ffmpeg_params["ffmpeg_parameters"]
        )
        
        # Join or change stream using optimized call manager
        if is_active:
            await call_manager.change_stream(chat_id, track["url"])
        else:
            await call_manager.join_call(chat_id, track["url"])
        
        # Store active chat
        call_manager.active_chats[chat_id] = 0  # userbot index
        
        # Send Now Playing message with quality indicator
        await send_now_playing(chat_id, track, optimizer.config)
        
        logger.info(f"Started playback in chat {chat_id}: {track['title']} (Quality: {optimizer.config.quality.value})")
        
    except Exception as e:
        logger.exception(f"Failed to start playback in chat {chat_id}")
        await queue_manager.set_status(chat_id, "idle")


async def on_track_end(chat_id: int):
    """Handle track end - play next or stop."""
    logger.info(f"Track ended in chat {chat_id}")
    
    # Check for loop mode
    from bot.utils.database import db
    group = await db.get_group(chat_id)
    loop_mode = group.get("settings", {}).get("loop_mode", "none")
    
    if loop_mode == "track":
        # Get current track and re-queue it
        current = await queue_manager.get_current(chat_id)
        if current:
            await queue_manager.add_to_queue(
                chat_id=chat_id,
                title=current["title"],
                url=current["url"],
                duration=current["duration"],
                thumb=current.get("thumb"),
                requested_by=current.get("requested_by"),
                source=current.get("source", "youtube")
            )
    
    # Continue to next track
    await start_playback(chat_id)


async def send_now_playing(chat_id: int, track: dict, audio_config=None):
    """Send now playing message with quality indicator."""
    try:
        # Generate thumbnail
        thumb_data = await generate_np_thumbnail(
            title=track["title"],
            artist=track.get("uploader", ""),
            duration=track["duration"],
            position=0,
            thumbnail_url=track.get("thumb"),
            source=track.get("source", "youtube")
        )
        
        # Build text
        duration_str = format_duration(track["duration"])
        
        # Add quality badge if audio config available
        quality_badge = ""
        if audio_config:
            quality_emoji = {
                "standard": "🎵",
                "high": "🎧", 
                "premium": "⭐",
                "lossless": "💎"
            }.get(audio_config.quality.value, "🎵")
            quality_badge = f"{quality_emoji} `{audio_config.quality.value.upper()}` | `{audio_config.bitrate}kbps`"
        
        text = f"""
🎵 **Now Playing** {quality_badge}

**{truncate_text(track['title'], 50)}**
⏱ Duration: `{duration_str}`
        """
        
        # Control buttons
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸", callback_data="pause"),
                InlineKeyboardButton("⏭", callback_data="skip"),
                InlineKeyboardButton("⏹", callback_data="stop"),
            ],
            [
                InlineKeyboardButton("🔁", callback_data="loop"),
                InlineKeyboardButton("📋 Queue", callback_data="queue"),
            ]
        ])
        
        # Send message
        if thumb_data:
            msg = await bot_client.send_photo(
                chat_id=chat_id,
                photo=thumb_data,
                caption=text,
                reply_markup=buttons
            )
        else:
            msg = await bot_client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=buttons
            )
        
        # Store for updates
        _np_messages[chat_id] = msg
        
    except Exception as e:
        logger.error(f"Failed to send now playing: {e}")


async def add_track_and_play(message: Message, chat_id: int, user_id: int, track: dict, search_msg: Message = None):
    """Add track to queue and start playback if needed."""
    # Check if already playing
    status = await queue_manager.get_status(chat_id)
    is_playing = status == "playing"
    
    # Add to queue
    position = await queue_manager.add_to_queue(
        chat_id=chat_id,
        title=track["title"],
        url=track["url"],
        duration=track["duration"],
        thumb=track.get("thumbnail"),
        requested_by=user_id,
        source=track.get("source", "youtube")
    )
    
    # Generate thumbnail
    thumb_data = await generate_np_thumbnail(
        title=track["title"],
        artist=track.get("uploader", ""),
        duration=track["duration"],
        position=0,
        thumbnail_url=track.get("thumbnail"),
        source=track.get("source", "youtube")
    )
    
    # Build response
    duration_str = format_duration(track["duration"])
    
    if is_playing:
        # Added to queue
        text = f"""
✅ **Added to Queue** at position {position}

🎵 **{truncate_text(track['title'], 50)}**
⏱ Duration: `{duration_str}`
👤 Requested by: {message.from_user.mention}
        """
        
        if search_msg:
            if thumb_data:
                await search_msg.delete()
                await message.reply_photo(photo=thumb_data, caption=text)
            else:
                await search_msg.edit(text)
        else:
            if thumb_data:
                await message.reply_photo(photo=thumb_data, caption=text)
            else:
                await message.reply(text)
    else:
        # Start playing immediately
        if search_msg:
            await search_msg.edit("🎵 Starting playback...")
        
        # Start playback
        await start_playback(chat_id)
        
        # Now playing message will be sent by the playback start
        if search_msg:
            await search_msg.delete()


async def show_conflict_options(message: Message, chat_id: int, user_id: int, conflicts: list, search_msg: Message):
    """Show conflict resolution options with inline buttons."""
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Build inline keyboard
    buttons = []
    row = []
    for i, track in enumerate(conflicts[:5], 1):
        title = track.get('title', 'Unknown')[:20] + "..." if len(track.get('title', '')) > 20 else track.get('title', 'Unknown')
        row.append(InlineKeyboardButton(f"{i}. {title}", callback_data=f"play_select_{i-1}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Add cancel button
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="play_cancel")])
    
    # Build text
    text = "🔍 **Multiple songs found with similar titles:**\n\n"
    for i, track in enumerate(conflicts[:5], 1):
        title = track.get('title', 'Unknown')
        artist = track.get('uploader', track.get('artist', 'Unknown Artist'))
        duration = track.get('duration', 0)
        mins, secs = divmod(int(duration), 60)
        duration_str = f"{mins}:{secs:02d}"
        similarity = track.get('_similarity', 0)
        match = "⭐ " if similarity > 0.9 else ""
        text += f"{i}. {match}**{title}**\n   👤 {artist} | ⏱ {duration_str}\n\n"
    
    text += "Click a button to select which song to play:"
    
    # Store pending conflict
    _pending_conflicts[chat_id] = {
        user_id: {
            'message_id': message.id,
            'tracks': conflicts[:5],
            'original_msg': search_msg,
            'user_mention': message.from_user.mention
        }
    }
    
    # Update message with options
    await search_msg.edit(text, reply_markup=InlineKeyboardMarkup(buttons))

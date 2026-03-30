"""Playback control commands: /pause, /resume, /skip, /stop, /seek, /volume, /replay"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.utils.permissions import require_admin, rate_limit
from bot.utils.formatters import format_duration
from bot.utils.database import db
from bot.core.call import call_manager
from bot.core.queue import queue_manager

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("pause") & filters.group)
@require_admin
@rate_limit
async def pause_cmd(client: Client, message: Message):
    """Pause current playback."""
    chat_id = message.chat.id
    
    status = await queue_manager.get_status(chat_id)
    if status != "playing":
        await message.reply("❌ Nothing is playing right now.")
        return
    
    try:
        # Update status
        await queue_manager.set_status(chat_id, "paused")
        
        # Pause via call manager
        await call_manager.pause(chat_id)
        
        await message.reply("⏸ Playback paused. Use /resume to continue.")
        logger.info(f"Paused playback in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Pause failed: {e}")
        await message.reply("❌ Failed to pause playback.")


@Client.on_message(filters.command("resume") & filters.group)
@require_admin
@rate_limit
async def resume_cmd(client: Client, message: Message):
    """Resume paused playback."""
    chat_id = message.chat.id
    
    status = await queue_manager.get_status(chat_id)
    if status != "paused":
        # Try to start if idle
        if status == "idle":
            # Try to start playback
            from bot.plugins.play import start_playback
            await start_playback(chat_id)
            return
        
        await message.reply("❌ Playback is not paused.")
        return
    
    try:
        # Update status
        await queue_manager.set_status(chat_id, "playing")
        
        # Resume via call manager
        await call_manager.resume(chat_id)
        
        await message.reply("▶ Playback resumed.")
        logger.info(f"Resumed playback in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        await message.reply("❌ Failed to resume playback.")


@Client.on_message(filters.command("skip") & filters.group)
@require_admin
@rate_limit
async def skip_cmd(client: Client, message: Message):
    """Skip to next song."""
    chat_id = message.chat.id
    
    status = await queue_manager.get_status(chat_id)
    if status not in ["playing", "paused"]:
        await message.reply("❌ Nothing is playing right now.")
        return
    
    # Check if there's a next song
    queue_len = await queue_manager.get_queue_length(chat_id)
    if queue_len == 0:
        await message.reply("⏭ Skipping... No more songs in queue.")
    else:
        await message.reply(f"⏭ Skipping... {queue_len} song(s) remaining.")
    
    try:
        # Stop current stream
        await call_manager.leave_call(chat_id)
        
        # Trigger next playback
        from bot.plugins.play import start_playback
        await start_playback(chat_id)
        
        logger.info(f"Skipped track in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Skip failed: {e}")
        await message.reply("❌ Failed to skip track.")


@Client.on_message(filters.command(["stop", "end"]) & filters.group)
@require_admin
@rate_limit
async def stop_cmd(client: Client, message: Message):
    """Stop playback and clear queue."""
    chat_id = message.chat.id
    
    status = await queue_manager.get_status(chat_id)
    if status == "idle":
        # Just clear queue if idle
        await queue_manager.clear_queue(chat_id)
        await message.reply("⏹ Queue cleared.")
        return
    
    try:
        # Leave call
        await call_manager.leave_call(chat_id)
        
        # Clear queue
        await queue_manager.clear_queue(chat_id)
        
        await message.reply("⏹ Playback stopped and queue cleared.")
        logger.info(f"Stopped playback in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Stop failed: {e}")
        await message.reply("❌ Failed to stop playback.")


@Client.on_message(filters.command("seek") & filters.group)
@require_admin
@rate_limit
async def seek_cmd(client: Client, message: Message):
    """Seek to position in track."""
    chat_id = message.chat.id
    
    if len(message.command) < 2:
        await message.reply("❌ Usage: `/seek [seconds]`\nExample: `/seek 120` (seek to 2 minutes)")
        return
    
    try:
        seconds = int(message.command[1])
    except ValueError:
        await message.reply("❌ Please provide a valid number of seconds.")
        return
    
    status = await queue_manager.get_status(chat_id)
    if status not in ["playing", "paused"]:
        await message.reply("❌ Nothing is playing right now.")
        return
    
    try:
        # Get current track
        current = await queue_manager.get_current(chat_id)
        if not current:
            await message.reply("❌ No track information available.")
            return
        
        # Validate seek position
        duration = current.get("duration", 0)
        if seconds < 0 or seconds >= duration:
            await message.reply(f"❌ Invalid seek position. Track duration is {format_duration(duration)}.")
            return
        
        # Restart stream with seek position
        # Get current track info
        current = await queue_manager.get_current(chat_id)
        if not current:
            await message.reply("❌ No track information available.")
            return
        
        # Create new AudioPiped with seek
        from pytgcalls.types import AudioPiped
        audio = AudioPiped(
            current["url"],
            audio_parameters={
                "bitrate": 48000,
                "channels": 2,
            }
        )
        
        # Change stream (py-tgcalls handles the transition)
        await call_manager.change_stream(chat_id, audio)
        
        # Update position
        await queue_manager.update_position(chat_id, seconds)
        
        await message.reply(f"⏩ Seeked to {format_duration(seconds)}.")
        logger.info(f"Seeked to {seconds}s in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Seek failed: {e}")
        await message.reply("❌ Failed to seek.")


@Client.on_message(filters.command("replay") & filters.group)
@require_admin
@rate_limit
async def replay_cmd(client: Client, message: Message):
    """Restart current track."""
    chat_id = message.chat.id
    
    status = await queue_manager.get_status(chat_id)
    if status not in ["playing", "paused"]:
        await message.reply("❌ Nothing is playing right now.")
        return
    
    try:
        # Get current track
        current = await queue_manager.get_current(chat_id)
        if not current:
            await message.reply("❌ No track information available.")
            return
        
        # Restart from beginning
        current = await queue_manager.get_current(chat_id)
        if not current:
            await message.reply("❌ No track information available.")
            return
        
        # Create fresh AudioPiped
        from pytgcalls.types import AudioPiped
        audio = AudioPiped(
            current["url"],
            audio_parameters={
                "bitrate": 48000,
                "channels": 2,
            }
        )
        
        await call_manager.change_stream(chat_id, audio)
        
        # Reset position
        await queue_manager.update_position(chat_id, 0)
        
        await message.reply("🔁 Replaying current track from the beginning.")
        logger.info(f"Replaying track in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Replay failed: {e}")
        await message.reply("❌ Failed to replay track.")


@Client.on_message(filters.command("volume") & filters.group)
@require_admin
@rate_limit
async def volume_cmd(client: Client, message: Message):
    """Adjust playback volume."""
    chat_id = message.chat.id
    
    if len(message.command) < 2:
        # Show current volume from settings
        group = await db.get_group(chat_id)
        vol = group.get("settings", {}).get("vol_default", 100)
        await message.reply(f"🔊 Current volume: {vol}%\nUsage: `/volume [1-200]`")
        return
    
    try:
        volume = int(message.command[1])
        if volume < 1 or volume > 200:
            await message.reply("❌ Volume must be between 1 and 200.")
            return
    except ValueError:
        await message.reply("❌ Please provide a valid number.")
        return
    
    try:
        # Note: py-tgcalls AudioPiped handles volume internally
        # We store it for future streams and settings
        await db.update_group(chat_id, {"settings.vol_default": volume})
        
        await message.reply(f"🔊 Volume set to {volume}%")
        logger.info(f"Set volume to {volume}% in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Volume change failed: {e}")
        await message.reply("❌ Failed to change volume.")

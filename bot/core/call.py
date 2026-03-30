"""py-tgcalls wrapper for Telegram Video Chat (formerly Voice Chat) management."""

import logging
import asyncio
from typing import Dict, Optional, Callable, List, Any
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioVideoPiped
from pytgcalls.types.stream import StreamAudioEnded
from pytgcalls.exceptions import GroupCallNotFound, NoActiveGroupCall

from bot.utils.audio_config import get_audio_optimizer, AudioConfig, AudioQuality

logger = logging.getLogger(__name__)

# Global call manager instance
call_manager = None


class CallManager:
    """Manages voice chat connections and audio streaming."""
    
    def __init__(self, userbot_clients: list):
        self.userbots = userbot_clients
        self.calls: Dict[int, PyTgCalls] = {}  # userbot_idx -> PyTgCalls
        self.active_chats: Dict[int, int] = {}  # chat_id -> userbot_idx
        self.on_stream_end_handlers: List[Callable] = []
        
    async def init(self):
        """Initialize py-tgcalls for each userbot."""
        for i, userbot in enumerate(self.userbots):
            call = PyTgCalls(userbot)
            await call.start()
            
            # Register event handlers
            call.on_stream_end()(self._on_stream_end)
            call.on_kicked()(self._on_kicked)
            call.on_closed_voice_chat()(self._on_closed_voice_chat)
            call.on_left()(self._on_left)
            
            self.calls[i] = call
            logger.info(f"py-tgcalls initialized for userbot {i+1}")
    
    async def join_call(
        self, 
        chat_id: int, 
        audio_path: str,
        video: bool = False,
        userbot_idx: int = 0,
        seek: Optional[int] = None
    ):
        """Join a Video Chat and start streaming high-quality audio.
        
        Args:
            chat_id: Telegram chat ID
            audio_path: Path or URL to audio file
            video: Whether to stream video
            userbot_idx: Which userbot to use
            seek: Optional seek position in seconds
        """
        call = self.calls.get(userbot_idx)
        if not call:
            raise RuntimeError(f"No call instance for userbot {userbot_idx}")
        
        # Get optimized audio configuration
        optimizer = get_audio_optimizer()
        ffmpeg_params = optimizer.get_ffmpeg_params(audio_path, seek)
        
        try:
            if video:
                # Video mode - AudioVideoPiped with high-quality audio
                stream = AudioVideoPiped(
                    audio_path,
                    audio_parameters=ffmpeg_params["audio_parameters"],
                    ffmpeg_parameters=ffmpeg_params["ffmpeg_parameters"]
                )
                await call.join_group_call(chat_id, stream)
            else:
                # Audio only mode with high-quality parameters
                stream = AudioPiped(
                    audio_path,
                    audio_parameters=ffmpeg_params["audio_parameters"],
                    ffmpeg_parameters=ffmpeg_params["ffmpeg_parameters"]
                )
                await call.join_group_call(chat_id, stream)
            
            self.active_chats[chat_id] = userbot_idx
            logger.info(f"Joined Video Chat in chat {chat_id} with userbot {userbot_idx} (Quality: {optimizer.config.quality.value})")
            
        except NoActiveGroupCall:
            raise RuntimeError("No active video chat in this group. Please start a video chat first.")
        except GroupCallNotFound:
            raise RuntimeError("Video chat not found")
        except Exception as e:
            logger.error(f"Failed to join call: {e}")
            raise
    
    async def leave_call(self, chat_id: int):
        """Leave a voice chat."""
        userbot_idx = self.active_chats.get(chat_id)
        if userbot_idx is None:
            return
        
        call = self.calls.get(userbot_idx)
        if call:
            try:
                await call.leave_group_call(chat_id)
                logger.info(f"Left VC in chat {chat_id}")
            except Exception as e:
                logger.warning(f"Error leaving call: {e}")
        
        self.active_chats.pop(chat_id, None)
    
    async def change_stream(self, chat_id: int, audio_path: str, video: bool = False, seek: Optional[int] = None):
        """Change the current stream to a new audio source with optimized quality."""
        userbot_idx = self.active_chats.get(chat_id)
        if userbot_idx is None:
            raise RuntimeError("Not in a video chat")
        
        call = self.calls.get(userbot_idx)
        if not call:
            raise RuntimeError("Call instance not found")
        
        # Get optimized audio configuration
        optimizer = get_audio_optimizer()
        ffmpeg_params = optimizer.get_ffmpeg_params(audio_path, seek)
        
        try:
            if video:
                stream = AudioVideoPiped(
                    audio_path,
                    audio_parameters=ffmpeg_params["audio_parameters"],
                    ffmpeg_parameters=ffmpeg_params["ffmpeg_parameters"]
                )
                await call.change_stream(chat_id, stream)
            else:
                stream = AudioPiped(
                    audio_path,
                    audio_parameters=ffmpeg_params["audio_parameters"],
                    ffmpeg_parameters=ffmpeg_params["ffmpeg_parameters"]
                )
                await call.change_stream(chat_id, stream)
            
            logger.info(f"Changed stream in chat {chat_id} (Quality: {optimizer.config.quality.value})")
        except Exception as e:
            logger.error(f"Failed to change stream: {e}")
            raise
    
    async def pause(self, chat_id: int):
        """Pause current playback."""
        userbot_idx = self.active_chats.get(chat_id)
        if userbot_idx is not None:
            call = self.calls.get(userbot_idx)
            if call:
                await call.pause_stream(chat_id)
                logger.info(f"Paused stream in chat {chat_id}")
    
    async def resume(self, chat_id: int):
        """Resume playback."""
        userbot_idx = self.active_chats.get(chat_id)
        if userbot_idx is not None:
            call = self.calls.get(userbot_idx)
            if call:
                await call.resume_stream(chat_id)
                logger.info(f"Resumed stream in chat {chat_id}")
    
    async def mute(self, chat_id: int):
        """Mute the stream."""
        userbot_idx = self.active_chats.get(chat_id)
        if userbot_idx is not None:
            call = self.calls.get(userbot_idx)
            if call:
                await call.mute_stream(chat_id)
    
    async def unmute(self, chat_id: int):
        """Unmute the stream."""
        userbot_idx = self.active_chats.get(chat_id)
        if userbot_idx is not None:
            call = self.calls.get(userbot_idx)
            if call:
                await call.unmute_stream(chat_id)
    
    # Event handlers
    async def _on_stream_end(self, client, update: StreamAudioEnded):
        """Handle stream end event - triggers next song."""
        chat_id = update.chat_id
        logger.info(f"Stream ended in chat {chat_id}")
        
        # Notify handlers (queue manager will pick this up)
        for handler in self.on_stream_end_handlers:
            try:
                await handler(chat_id)
            except Exception as e:
                logger.error(f"Error in stream end handler: {e}")
    
    async def _on_kicked(self, client, update):
        """Handle being kicked from VC."""
        chat_id = update.chat_id
        logger.warning(f"Kicked from VC in chat {chat_id}")
        self.active_chats.pop(chat_id, None)
        
        # Clean state
        from bot.core.queue import queue_manager
        await queue_manager.clear_queue(chat_id)
    
    async def _on_closed_voice_chat(self, client, update):
        """Handle VC being closed."""
        chat_id = update.chat_id
        logger.info(f"Voice chat closed in chat {chat_id}")
        self.active_chats.pop(chat_id, None)
    
    async def _on_left(self, client, update):
        """Handle leaving VC."""
        chat_id = update.chat_id
        logger.info(f"Left VC in chat {chat_id}")
        self.active_chats.pop(chat_id, None)
    
    def on_stream_end(self, func: Callable):
        """Decorator to register stream end handler."""
        self.on_stream_end_handlers.append(func)
        return func


async def init_calls(userbot_clients: list):
    """Initialize the global call manager."""
    global call_manager
    call_manager = CallManager(userbot_clients)
    await call_manager.init()

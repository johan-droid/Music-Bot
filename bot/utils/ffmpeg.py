"""FFmpeg audio pipeline for streaming to py-tgcalls."""

import logging
import asyncio
import subprocess
import os
from typing import Optional, Callable
from config import config

logger = logging.getLogger(__name__)

# FFmpeg PCM output settings per SRS specification
FFMPEG_FLAGS = [
    "-probesize", "50M",           # Faster format detection
    "-analyzeduration", "20M",     # Reduce cold-start delay
    "-reconnect", "1",             # Auto-reconnect on drop
    "-reconnect_streamed", "1",    # Enable for live streams
    "-reconnect_delay_max", "5",   # Max 5s reconnect wait
    "-vn",                         # Audio only
    "-f", "s16le",                 # PCM signed 16-bit little-endian
    "-ar", "48000",                # 48kHz sample rate
    "-ac", "2",                    # Stereo
    "-bufsize", "8192k",           # 8MB buffer
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",  # EBU R128 loudness normalization
    "pipe:1",                      # Output to stdout
]


class FFmpegPipeline:
    """Manages FFmpeg subprocess for audio streaming."""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.input_url: Optional[str] = None
        self.on_data: Optional[Callable] = None
        self.on_end: Optional[Callable] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.volume = 100  # Volume level (affects FFmpeg filter)
    
    def _build_command(self, input_url: str, seek: int = 0) -> list:
        """Build FFmpeg command with current settings.
        
        Args:
            input_url: Input audio URL or file path
            seek: Seek position in seconds
            
        Returns:
            Command list for subprocess
        """
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
        
        # Input options
        if input_url.startswith("http://") or input_url.startswith("https://"):
            # Network stream
            cmd.extend(["-i", input_url])
        else:
            # Local file
            cmd.extend(["-i", input_url])
        
        # Seek if needed
        if seek > 0:
            cmd.extend(["-ss", str(seek)])
        
        # Build audio filter with volume
        af = "loudnorm=I=-16:TP=-1.5:LRA=11"
        if self.volume != 100:
            # Apply volume adjustment
            vol = self.volume / 100.0
            af = f"volume={vol:.2f},{af}"
        
        # Replace the -af flag with our custom one
        flags = FFMPEG_FLAGS.copy()
        af_idx = flags.index("-af")
        flags[af_idx + 1] = af
        
        cmd.extend(flags)
        
        return cmd
    
    async def start(
        self, 
        input_url: str, 
        seek: int = 0,
        on_data: Optional[Callable] = None,
        on_end: Optional[Callable] = None
    ):
        """Start FFmpeg pipeline.
        
        Args:
            input_url: Audio source URL or path
            seek: Seek position in seconds
            on_data: Callback for PCM data (optional)
            on_end: Callback when stream ends
        """
        self.input_url = input_url
        self.on_data = on_data
        self.on_end = on_end
        
        cmd = self._build_command(input_url, seek)
        
        logger.info(f"Starting FFmpeg: {' '.join(cmd[:5])}...")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=8192 * 1024,  # 8MB buffer
            )
            
            self._running = True
            
            # Start reader task
            self._task = asyncio.create_task(self._read_stream())
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            self._running = False
            raise
    
    async def _read_stream(self):
        """Read PCM data from FFmpeg stdout."""
        try:
            chunk_size = 1920  # 20ms of PCM at 48kHz stereo s16le
            
            while self._running and self.process:
                data = self.process.stdout.read(chunk_size)
                
                if not data:
                    # Stream ended
                    break
                
                if self.on_data:
                    await self.on_data(data)
                
                # Small yield to prevent blocking
                await asyncio.sleep(0)
                
        except Exception as e:
            if self._running:
                logger.error(f"FFmpeg read error: {e}")
        finally:
            self._running = False
            
            if self.on_end:
                try:
                    await self.on_end()
                except Exception as e:
                    logger.error(f"On end callback error: {e}")
    
    async def stop(self):
        """Stop FFmpeg pipeline."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(0.5)
                
                if self.process.poll() is None:
                    self.process.kill()
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.warning(f"Error stopping FFmpeg: {e}")
            finally:
                self.process = None
        
        logger.info("FFmpeg pipeline stopped")
    
    def set_volume(self, volume: int):
        """Set volume level (1-200)."""
        self.volume = max(1, min(200, volume))
    
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._running and self.process is not None
    
    async def restart(self):
        """Restart the stream from beginning."""
        if self.input_url:
            await self.stop()
            await asyncio.sleep(0.5)
            await self.start(self.input_url, 0, self.on_data, self.on_end)


class FFmpegManager:
    """Manages multiple FFmpeg pipelines for concurrent streams."""
    
    def __init__(self):
        self.pipelines: dict = {}  # chat_id -> FFmpegPipeline
    
    async def start_stream(
        self, 
        chat_id: int, 
        input_url: str,
        seek: int = 0,
        on_data: Optional[Callable] = None,
        on_end: Optional[Callable] = None
    ):
        """Start a stream for a chat."""
        # Stop existing if any
        if chat_id in self.pipelines:
            await self.pipelines[chat_id].stop()
        
        pipeline = FFmpegPipeline()
        await pipeline.start(input_url, seek, on_data, on_end)
        
        self.pipelines[chat_id] = pipeline
        logger.info(f"Started stream for chat {chat_id}")
    
    async def stop_stream(self, chat_id: int):
        """Stop stream for a chat."""
        if chat_id in self.pipelines:
            await self.pipelines[chat_id].stop()
            del self.pipelines[chat_id]
            logger.info(f"Stopped stream for chat {chat_id}")
    
    async def set_volume(self, chat_id: int, volume: int):
        """Set volume for a chat's stream."""
        if chat_id in self.pipelines:
            self.pipelines[chat_id].set_volume(volume)
            logger.info(f"Set volume to {volume} for chat {chat_id}")
    
    def get_pipeline(self, chat_id: int) -> Optional[FFmpegPipeline]:
        """Get pipeline for a chat."""
        return self.pipelines.get(chat_id)


# Global manager
ffmpeg_manager = FFmpegManager()

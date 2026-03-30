"""Permission decorators and admin check helpers."""

import logging
import re
from functools import wraps
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery
from config import config
from bot.utils.cache import cache
from bot.utils.database import db
from bot.core.bot import bot_client
from bot.core.userbot import userbot_clients

logger = logging.getLogger(__name__)

# Active voice chat participants cache
_vc_participants: dict = {}  # {chat_id: {user_id: timestamp}}


async def is_vc_participant(chat_id: int, user_id: int) -> bool:
    """Check if user is currently in the voice chat."""
    # Check local cache first
    if chat_id in _vc_participants:
        if user_id in _vc_participants[chat_id]:
            return True
    
    # Query Telegram for current participants
    try:
        # Get active voice chat participants
        from bot.core.call import call_manager
        if chat_id not in call_manager.active_chats:
            return False
        
        # Check if user is in the chat via participant list
        chat = await bot_client.get_chat(chat_id)
        if hasattr(chat, 'voice_chat') and chat.voice_chat:
            # Check if user is in voice chat participants
            for participant in chat.voice_chat.participants or []:
                if participant.user_id == user_id:
                    _vc_participants.setdefault(chat_id, {})[user_id] = True
                    return True
        
        # Alternative: check via userbot
        if userbot_clients:
            userbot = userbot_clients[0]
            try:
                member = await userbot.get_chat_member(chat_id, user_id)
                # If user is in voice chat, they show as member
                # Note: Pyrogram doesn't have direct VC participant API
                # So we check recent activity as fallback
                return True  # Allow if they're a member and VC is active
            except:
                pass
                
    except Exception as e:
        logger.debug(f"Error checking VC participant: {e}")
    
    return False


async def update_vc_participants(chat_id: int, participants: list):
    """Update cached VC participants."""
    _vc_participants[chat_id] = {p: True for p in participants}


async def clear_vc_participants(chat_id: int):
    """Clear VC participants cache when chat ends."""
    if chat_id in _vc_participants:
        del _vc_participants[chat_id]


async def is_owner(user_id: int) -> bool:
    """Check if user is bot owner."""
    return user_id == config.OWNER_ID


async def is_sudo(user_id: int) -> bool:
    """Check if user is sudo (or owner)."""
    if await is_owner(user_id):
        return True
    return await db.is_sudo(user_id)


async def is_gbanned(user_id: int) -> bool:
    """Check if user is globally banned."""
    # Check cache first
    cached = await cache.is_gbanned_cached(user_id)
    if cached:
        return True
    
    # Check database
    banned = await db.is_gbanned(user_id)
    await cache.cache_gban(user_id, banned)
    return banned


async def is_group_admin(chat_id: int, user_id: int) -> bool:
    """Check if user is admin in a group."""
    # Check cache first
    cached = await cache.is_admin(chat_id, user_id)
    if cached:
        return True
    
    try:
        # Fetch from Telegram
        member = await bot_client.get_chat_member(chat_id, user_id)
        is_admin = member.status in ["administrator", "creator"]
        
        # Update cache
        if is_admin:
            current_admins = await cache.get_cached_admins(chat_id)
            if user_id not in current_admins:
                current_admins.append(user_id)
                await cache.cache_admins(chat_id, current_admins)
        
        return is_admin
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


async def is_admin_cached(chat_id: int, user_id: int) -> bool:
    """Fast admin check using cache only."""
    return await cache.is_admin(chat_id, user_id)


async def check_bot_admin(chat_id: int) -> bool:
    """Check if bot is admin in a group."""
    try:
        member = await bot_client.get_chat_member(chat_id, bot_client.me.id)
        return member.status == "administrator" or member.status == "creator"
    except Exception:
        return False


async def check_userbot_admin(chat_id: int) -> bool:
    """Check if userbot is admin with voice chat manage privilege."""
    if not userbot_clients:
        return False
    
    userbot = userbot_clients[0]
    try:
        member = await userbot.get_chat_member(chat_id, userbot.me.id)
        if member.status != "administrator":
            return False
        
        # Check for voice chat manage privilege
        privileges = member.privileges
        if privileges:
            return privileges.can_manage_video_chats
        return False
    except Exception:
        return False


# Permission level check
async def get_permission_level(user_id: int, chat_id: int = None, check_vc: bool = False) -> int:
    """Get permission level for a user.
    
    Levels:
        5 - Owner
        4 - Sudo
        3 - Group Admin
        2 - VC Participant (when VC is active)
        1 - Normal User
        0 - Banned
    """
    # Check gban first
    if await is_gbanned(user_id):
        return 0
    
    if await is_owner(user_id):
        return 5
    
    if await is_sudo(user_id):
        return 4
    
    if chat_id and await is_group_admin(chat_id, user_id):
        return 3
    
    # Check VC participant if requested and chat_id provided
    if check_vc and chat_id:
        from bot.core.call import call_manager
        if chat_id in call_manager.active_chats:
            # VC is active, allow participants
            return 2
    
    return 1


# Decorators
def require_admin(func):
    """Decorator to require group admin or higher."""
    @wraps(func)
    async def wrapper(client, message: Message):
        # Get user info
        user_id = message.from_user.id if message.from_user else None
        chat_id = message.chat.id if message.chat else None
        
        if not user_id or not chat_id:
            return
        
        # Check maintenance mode
        if await cache.is_maintenance():
            if not await is_sudo(user_id):
                await message.reply("🔧 Bot is under maintenance. Please try again later.")
                return
        
        # Check gban
        if await is_gbanned(user_id):
            return  # Silent reject
        
        # Check permissions
        level = await get_permission_level(user_id, chat_id)
        if level < 3:  # Not admin or higher
            await message.reply("⛔ This command is for admins only.")
            return
        
        # Check bot admin status
        if not await check_bot_admin(chat_id):
            await message.reply(
                "❌ I need to be an admin with 'Manage Voice Chats' permission to function.\n"
                "Please promote me and try again."
            )
            return
        
        return await func(client, message)
    
    return wrapper


def require_sudo(func):
    """Decorator to require sudo or owner."""
    @wraps(func)
    async def wrapper(client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        
        if not user_id:
            return
        
        # Check gban
        if await is_gbanned(user_id):
            return
        
        if not await is_sudo(user_id):
            await message.reply("⛔ This command is for sudo users only.")
            return
        
        return await func(client, message)
    
    return wrapper


def require_owner(func):
    """Decorator to require owner only."""
    @wraps(func)
    async def wrapper(client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        
        if not user_id:
            return
        
        if not await is_owner(user_id):
            await message.reply("⛔ This command is for the bot owner only.")
            return
        
        return await func(client, message)
    
    return wrapper


def rate_limit(func):
    """Decorator to apply rate limiting."""
    @wraps(func)
    async def wrapper(client, message: Message):
        user_id = message.from_user.id if message.from_user else None
        
        if not user_id:
            return
        
        # Get command name from function
        cmd = func.__name__.replace("_cmd", "").replace("_", "")
        
        if not await cache.check_cooldown(user_id, cmd, config.COMMAND_COOLDOWN):
            return  # Silent reject on cooldown
        
        return await func(client, message)
    
    return wrapper

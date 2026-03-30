"""Admin commands: /addsudo, /delsudo, /sudolist, /gban, /ungban, /block, /unblock, /stats, /broadcast, /restart, /maintenance"""

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import config
from bot.utils.permissions import require_owner, require_sudo, get_permission_level
from bot.utils.cache import cache
from bot.utils.database import db
from bot.core.bot import bot_client

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("addsudo") & filters.private)
@require_owner
async def addsudo_cmd(client: Client, message: Message):
    """Grant sudo privileges to a user (owner only)."""
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/addsudo [user_id]` or reply to a user.")
        return
    
    # Get user ID
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        name = message.reply_to_message.from_user.first_name
    else:
        try:
            user_id = int(message.command[1])
            # Get user info
            user = await client.get_users(user_id)
            name = user.first_name
        except Exception:
            await message.reply("❌ Invalid user ID.")
            return
    
    # Check if already sudo
    if await db.is_sudo(user_id):
        await message.reply("ℹ️ User is already a sudo user.")
        return
    
    # Add sudo
    await db.add_sudo(user_id, name, message.from_user.id)
    await message.reply(f"✅ Added **{name}** (`{user_id}`) as sudo user.")
    logger.info(f"Added sudo user {user_id}")


@Client.on_message(filters.command("delsudo") & filters.private)
@require_owner
async def delsudo_cmd(client: Client, message: Message):
    """Revoke sudo privileges (owner only)."""
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/delsudo [user_id]` or reply to a user.")
        return
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
    
    # Cannot remove owner
    if user_id == config.OWNER_ID:
        await message.reply("❌ Cannot remove the bot owner.")
        return
    
    # Remove sudo
    await db.remove_sudo(user_id)
    await message.reply(f"✅ Removed user `{user_id}` from sudo list.")
    logger.info(f"Removed sudo user {user_id}")


@Client.on_message(filters.command("sudolist") & filters.private)
@require_owner
async def sudolist_cmd(client: Client, message: Message):
    """List all sudo users (owner only)."""
    sudos = await db.get_sudo_users()
    
    if not sudos:
        await message.reply("📭 No sudo users.")
        return
    
    lines = ["👑 **Sudo Users**\n"]
    for sudo in sudos:
        lines.append(f"• `{sudo['_id']}` - {sudo.get('name', 'Unknown')}")
    
    await message.reply("\n".join(lines))


@Client.on_message(filters.command("gban") & filters.group)
@require_sudo
async def gban_cmd(client: Client, message: Message):
    """Globally ban a user (sudo+)."""
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/gban [user_id]` or reply to a user.")
        return
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
    
    # Cannot ban owner or sudo
    if user_id == config.OWNER_ID:
        await message.reply("❌ Cannot ban the bot owner.")
        return
    
    if await db.is_sudo(user_id):
        await message.reply("❌ Cannot ban a sudo user.")
        return
    
    # Get reason
    reason = "No reason provided"
    if len(message.command) > 2:
        reason = " ".join(message.command[2:])
    
    # Add gban
    await db.gban_user(user_id, reason, message.from_user.id)
    await cache.cache_gban(user_id, True)
    
    await message.reply(f"🚫 Globally banned user `{user_id}`.\n**Reason:** {reason}")
    logger.warning(f"Globally banned user {user_id} by {message.from_user.id}")


@Client.on_message(filters.command("ungban") & filters.group)
@require_sudo
async def ungban_cmd(client: Client, message: Message):
    """Remove global ban (sudo+)."""
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/ungban [user_id]` or reply to a user.")
        return
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
    
    # Remove gban
    await db.ungban_user(user_id)
    await cache.cache_gban(user_id, False)
    
    await message.reply(f"✅ Removed global ban for user `{user_id}`.")
    logger.info(f"Removed gban for user {user_id}")


@Client.on_message(filters.command("block") & filters.group)
@require_sudo
async def block_cmd(client: Client, message: Message):
    """Block user in this group only."""
    chat_id = message.chat.id
    
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/block [user_id]` or reply to a user.")
        return
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
    
    await db.ban_user(chat_id, user_id)
    await message.reply(f"🚫 Blocked user `{user_id}` in this group.")


@Client.on_message(filters.command("unblock") & filters.group)
@require_sudo
async def unblock_cmd(client: Client, message: Message):
    """Unblock user in this group."""
    chat_id = message.chat.id
    
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/unblock [user_id]` or reply to a user.")
        return
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
    
    await db.unban_user(chat_id, user_id)
    await message.reply(f"✅ Unblocked user `{user_id}` in this group.")


@Client.on_message(filters.command("stats") & filters.group)
@require_sudo
async def stats_cmd(client: Client, message: Message):
    """Show bot statistics (sudo+)."""
    stats = await db.get_stats()
    
    text = f"""
📊 **Bot Statistics**

👥 **Groups:**
• Total: `{stats['total_groups']}`
• Active: `{stats['active_groups']}`

👑 **Permissions:**
• Sudo users: `{stats['sudo_users']}`
• Globally banned: `{stats['gbanned_users']}`

🔧 **System:**
• Uptime: Check logs
• Version: 1.0.0
    """
    
    await message.reply(text)


@Client.on_message(filters.command("broadcast") & filters.private)
@require_sudo
async def broadcast_cmd(client: Client, message: Message):
    """Broadcast message to all groups (sudo+)."""
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: `/broadcast [message]` or reply to a message.")
        return
    
    # Get message to broadcast
    if message.reply_to_message:
        broadcast_msg = message.reply_to_message
    else:
        broadcast_text = " ".join(message.command[1:])
    
    # Send to all groups
    groups = await db.db.groups.find({"is_active": True}).to_list(length=None)
    
    status_msg = await message.reply(f"📢 Broadcasting to {len(groups)} groups...")
    
    success = 0
    failed = 0
    
    for group in groups:
        try:
            if message.reply_to_message:
                await broadcast_msg.copy(group["_id"])
            else:
                await bot_client.send_message(group["_id"], broadcast_text)
            success += 1
            await asyncio.sleep(0.1)  # Rate limit
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed for {group['_id']}: {e}")
    
    await status_msg.edit(f"✅ Broadcast complete!\nSuccess: {success}\nFailed: {failed}")


@Client.on_message(filters.command("restart") & filters.private)
@require_owner
async def restart_cmd(client: Client, message: Message):
    """Restart bot (owner only)."""
    await message.reply("🔄 Restarting bot...")
    logger.info(f"Restart requested by {message.from_user.id}")
    
    # Graceful shutdown
    import sys
    sys.exit(0)  # Docker/Supervisor will restart


@Client.on_message(filters.command("maintenance") & filters.private)
@require_owner
async def maintenance_cmd(client: Client, message: Message):
    """Toggle maintenance mode (owner only)."""
    if len(message.command) < 2:
        current = await cache.is_maintenance()
        status = "🔧 ON" if current else "✅ OFF"
        await message.reply(f"Maintenance mode: {status}\nUsage: `/maintenance [on/off]`")
        return
    
    arg = message.command[1].lower()
    
    if arg in ["on", "true", "1", "yes"]:
        await cache.set_maintenance(True)
        await message.reply("🔧 Maintenance mode enabled.\nOnly sudo users can use the bot.")
        logger.warning(f"Maintenance mode enabled by {message.from_user.id}")
    
    elif arg in ["off", "false", "0", "no"]:
        await cache.set_maintenance(False)
        await message.reply("✅ Maintenance mode disabled.\nBot is now available to all users.")
        logger.info(f"Maintenance mode disabled by {message.from_user.id}")
    
    else:
        await message.reply("❌ Invalid argument. Use `on` or `off`.")

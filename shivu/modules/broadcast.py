"""
Broadcast Module
Handles broadcasting messages to all users and groups.
"""

import asyncio
from html import escape
from typing import List, Dict

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, pm_users, top_global_groups_collection, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import to_small_caps


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast <message> - Broadcast message to all users (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            to_small_caps("Usage: /broadcast <message>\n"
                         "Or reply to a message with /broadcast")
        )
        return
    
    # Get message to broadcast
    if update.message.reply_to_message:
        broadcast_message = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    else:
        broadcast_message = " ".join(context.args)
    
    if not broadcast_message:
        await update.message.reply_text(to_small_caps("❌ Cannot broadcast empty message."))
        return
    
    # Get all users
    try:
        users = []
        async for doc in pm_users.find({}):
            users.append(doc.get('user_id'))
        
        users = list(set(users))  # Remove duplicates
    except Exception as e:
        LOGGER.error(f"Error fetching users for broadcast: {e}")
        await update.message.reply_text(to_small_caps("❌ Error fetching user list."))
        return
    
    if not users:
        await update.message.reply_text(to_small_caps("❌ No users to broadcast to."))
        return
    
    # Send broadcast
    sent = 0
    failed = 0
    
    status_message = await update.message.reply_text(
        to_small_caps(f"📢 Broadcasting to {len(users)} users...")
    )
    
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"<b>{to_small_caps('📢 Broadcast')}</b>\n\n{broadcast_message}",
                parse_mode='HTML'
            )
            sent += 1
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)
            
        except Exception as e:
            LOGGER.warning(f"Failed to send broadcast to {user_id}: {e}")
            failed += 1
    
    # Update status
    await status_message.edit_text(
        f"✅ <b>{to_small_caps('Broadcast Complete')}</b>\n\n"
        f"📤 {to_small_caps('Sent:')} {sent}\n"
        f"❌ {to_small_caps('Failed:')} {failed}\n"
        f"📊 {to_small_caps('Total:')} {len(users)}",
        parse_mode='HTML'
    )


async def broadcast_groups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcastgroups <message> - Broadcast message to all groups (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            to_small_caps("Usage: /broadcastgroups <message>\n"
                         "Or reply to a message with /broadcastgroups")
        )
        return
    
    # Get message to broadcast
    if update.message.reply_to_message:
        broadcast_message = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    else:
        broadcast_message = " ".join(context.args)
    
    if not broadcast_message:
        await update.message.reply_text(to_small_caps("❌ Cannot broadcast empty message."))
        return
    
    # Get all groups
    try:
        groups = []
        async for doc in top_global_groups_collection.find({}):
            groups.append(doc.get('group_id'))
        
        groups = list(set(groups))  # Remove duplicates
    except Exception as e:
        LOGGER.error(f"Error fetching groups for broadcast: {e}")
        await update.message.reply_text(to_small_caps("❌ Error fetching group list."))
        return
    
    if not groups:
        await update.message.reply_text(to_small_caps("❌ No groups to broadcast to."))
        return
    
    # Send broadcast
    sent = 0
    failed = 0
    
    status_message = await update.message.reply_text(
        to_small_caps(f"📢 Broadcasting to {len(groups)} groups...")
    )
    
    for group_id in groups:
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=f"<b>{to_small_caps('📢 Broadcast')}</b>\n\n{broadcast_message}",
                parse_mode='HTML'
            )
            sent += 1
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)
            
        except Exception as e:
            LOGGER.warning(f"Failed to send broadcast to group {group_id}: {e}")
            failed += 1
    
    # Update status
    await status_message.edit_text(
        f"✅ <b>{to_small_caps('Group Broadcast Complete')}</b>\n\n"
        f"📤 {to_small_caps('Sent:')} {sent}\n"
        f"❌ {to_small_caps('Failed:')} {failed}\n"
        f"📊 {to_small_caps('Total:')} {len(groups)}",
        parse_mode='HTML'
    )


# Register handlers
application.add_handler(CommandHandler("broadcast", broadcast_cmd, block=False))
application.add_handler(CommandHandler("broadcastgroups", broadcast_groups_cmd, block=False))

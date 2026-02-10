"""
ChangeTime Module
Handles changing message frequency and other time-based settings.
"""

from html import escape
from typing import Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, user_totals_collection, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import to_small_caps


async def changetime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/changetime <seconds> - Change character spawn frequency (Admin only)."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        # Check if user is admin in the group
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(to_small_caps("❌ Only group admins can use this command."))
                return
        except Exception as e:
            LOGGER.error(f"Error checking admin status: {e}")
            await update.message.reply_text(to_small_caps("❌ Error checking permissions."))
            return
    
    if not context.args:
        # Show current frequency
        try:
            chat_data = await user_totals_collection.find_one({'chat_id': str(chat_id)})
            current_freq = chat_data.get('message_frequency', 100) if chat_data else 100
        except Exception:
            current_freq = 100
        
        await update.message.reply_text(
            f"<b>{to_small_caps('⏱️ Current Settings')}</b>\n\n"
            f"{to_small_caps('Spawn frequency:')} <code>{current_freq}</code> {to_small_caps('messages')}\n\n"
            f"{to_small_caps('Usage:')} <code>/changetime &lt;messages&gt;</code>\n"
            f"{to_small_caps('Example:')} <code>/changetime 50</code>\n\n"
            f"{to_small_caps('Lower = more frequent spawns')}\n"
            f"{to_small_caps('Higher = less frequent spawns')}",
            parse_mode='HTML'
        )
        return
    
    try:
        frequency = int(context.args[0])
        if frequency < 10:
            await update.message.reply_text(to_small_caps("❌ Frequency must be at least 10 messages."))
            return
        if frequency > 1000:
            await update.message.reply_text(to_small_caps("❌ Frequency cannot exceed 1000 messages."))
            return
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Please enter a valid number."))
        return
    
    # Update frequency
    try:
        await user_totals_collection.update_one(
            {'chat_id': str(chat_id)},
            {'$set': {'message_frequency': frequency}},
            upsert=True
        )
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Spawn Frequency Updated')}</b>\n\n"
            f"{to_small_caps('New frequency:')} <code>{frequency}</code> {to_small_caps('messages')}\n\n"
            f"{to_small_caps('Characters will now appear every')} {frequency} {to_small_caps('messages.')}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Spawn frequency changed to {frequency} in chat {chat_id} by user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"Error updating frequency: {e}")
        await update.message.reply_text(to_small_caps("❌ Error updating frequency."))


async def resettime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resettime - Reset spawn frequency to default (Admin only)."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        # Check if user is admin in the group
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(to_small_caps("❌ Only group admins can use this command."))
                return
        except Exception as e:
            LOGGER.error(f"Error checking admin status: {e}")
            await update.message.reply_text(to_small_caps("❌ Error checking permissions."))
            return
    
    # Reset frequency
    try:
        await user_totals_collection.update_one(
            {'chat_id': str(chat_id)},
            {'$set': {'message_frequency': 100}},
            upsert=True
        )
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Spawn Frequency Reset')}</b>\n\n"
            f"{to_small_caps('Frequency reset to default:')} <code>100</code> {to_small_caps('messages')}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Spawn frequency reset in chat {chat_id} by user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"Error resetting frequency: {e}")
        await update.message.reply_text(to_small_caps("❌ Error resetting frequency."))


async def gettime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gettime - Show current spawn frequency."""
    chat_id = update.effective_chat.id
    
    try:
        chat_data = await user_totals_collection.find_one({'chat_id': str(chat_id)})
        current_freq = chat_data.get('message_frequency', 100) if chat_data else 100
    except Exception:
        current_freq = 100
    
    await update.message.reply_text(
        f"<b>{to_small_caps('⏱️ Current Spawn Frequency')}</b>\n\n"
        f"{to_small_caps('Frequency:')} <code>{current_freq}</code> {to_small_caps('messages')}\n\n"
        f"{to_small_caps('Characters appear every')} {current_freq} {to_small_caps('messages in this chat.')}",
        parse_mode='HTML'
    )


# Register handlers
application.add_handler(CommandHandler("changetime", changetime_cmd, block=False))
application.add_handler(CommandHandler("resettime", resettime_cmd, block=False))
application.add_handler(CommandHandler("gettime", gettime_cmd, block=False))

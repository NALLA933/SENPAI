"""
SClaim Module
Special claim system for support group/channel.
"""

import time
import random
from html import escape
from typing import Dict, Optional
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, collection, user_collection, LOGGER
from shivu.config import Config
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity

# Configuration - use from Config
ALLOWED_GROUP_ID = Config.ALLOWED_GROUP_ID
SUPPORT_GROUP_ID = Config.SUPPORT_GROUP_ID
SUPPORT_CHANNEL_ID = Config.SUPPORT_CHANNEL_ID

# Claim cooldowns
claim_cooldowns: Dict[int, float] = {}
CLAIM_COOLDOWN_HOURS = 24

# Daily claim tracking
daily_claims: Dict[int, Dict] = {}


async def sclaim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sclaim - Claim a special character (Support group only)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if in allowed group
    if chat_id not in [ALLOWED_GROUP_ID, SUPPORT_GROUP_ID]:
        await update.message.reply_text(
            to_small_caps("❌ This command can only be used in the support group!")
        )
        return
    
    # Check cooldown
    now = time.time()
    if user_id in claim_cooldowns:
        last_claim = claim_cooldowns[user_id]
        cooldown_seconds = CLAIM_COOLDOWN_HOURS * 3600
        
        if now - last_claim < cooldown_seconds:
            remaining = cooldown_seconds - (now - last_claim)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            
            await update.message.reply_text(
                to_small_caps(f"⏱️ You can claim again in {hours}h {minutes}m.")
            )
            return
    
    # Get random character (prefer higher rarity)
    try:
        # Get characters with rarity 3+ (legendary and above)
        pipeline = [
            {"$match": {"rarity": {"$gte": 3}}},
            {"$sample": {"size": 10}}
        ]
        
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=10)
        
        if not characters:
            # Fallback to any character
            pipeline = [{"$sample": {"size": 5}}]
            cursor = collection.aggregate(pipeline)
            characters = await cursor.to_list(length=5)
        
    except Exception as e:
        LOGGER.error(f"Error fetching characters for sclaim: {e}")
        await update.message.reply_text(to_small_caps("❌ Error fetching characters. Please try again."))
        return
    
    if not characters:
        await update.message.reply_text(to_small_caps("❌ No characters available."))
        return
    
    # Select random character
    character = random.choice(characters)
    
    # Add to user's collection
    try:
        char_to_add = {
            'id': character.get('id'),
            'name': character.get('name'),
            'anime': character.get('anime'),
            'rarity': character.get('rarity'),
            'img_url': character.get('img_url')
        }
        
        await user_collection.update_one(
            {'id': user_id},
            {'$push': {'characters': char_to_add}},
            upsert=True
        )
        
        # Set cooldown
        claim_cooldowns[user_id] = now
        
        # Track daily claim
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in daily_claims:
            daily_claims[today] = {'count': 0, 'users': []}
        daily_claims[today]['count'] += 1
        if user_id not in daily_claims[today]['users']:
            daily_claims[today]['users'].append(user_id)
        
        # Format message
        char_name = escape(character.get('name', 'Unknown'))
        anime_name = escape(character.get('anime', 'Unknown'))
        rarity = parse_rarity(character.get('rarity'))
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        img_url = character.get('img_url', '')
        
        message = (
            f"✨ <b>{to_small_caps('Special Claim Successful!')}</b>\n\n"
            f"👤 {char_name}\n"
            f"🎬 {anime_name}\n"
            f"✨ {rarity_display}\n\n"
            f"{to_small_caps('Next claim available in')} {CLAIM_COOLDOWN_HOURS} {to_small_caps('hours')}"
        )
        
        # Send with image
        if img_url:
            await update.message.reply_photo(
                photo=img_url,
                caption=message,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(message, parse_mode='HTML')
        
        LOGGER.info(f"User {user_id} claimed special character {character.get('id')}")
        
    except Exception as e:
        LOGGER.error(f"Error processing sclaim: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing claim. Please try again."))


async def sclaiminfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sclaiminfo - Show sclaim information."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_data = daily_claims.get(today, {'count': 0, 'users': []})
    
    message = (
        f"<b>{to_small_caps('📊 SClaim Info')}</b>\n\n"
        f"⏰ {to_small_caps('Cooldown:')} {CLAIM_COOLDOWN_HOURS} hours\n"
        f"📅 {to_small_caps('Claims today:')} {today_data['count']}\n"
        f"👥 {to_small_caps('Unique users today:')} {len(today_data['users'])}\n\n"
        f"{to_small_caps('Use /sclaim to claim a special character!')}"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')


async def resetsclaim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resetsclaim <user_id> - Reset a user's sclaim cooldown (Admin only)."""
    from shivu import OWNER_ID, SUDO_USERS
    
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /resetsclaim <user_id>"))
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ User ID must be a number."))
        return
    
    if target_id in claim_cooldowns:
        del claim_cooldowns[target_id]
        await update.message.reply_text(
            to_small_caps(f"✅ SClaim cooldown reset for user {target_id}.")
        )
    else:
        await update.message.reply_text(
            to_small_caps(f"ℹ️ User {target_id} has no active cooldown.")
        )


# Register handlers
application.add_handler(CommandHandler("sclaim", sclaim_cmd, block=False))
application.add_handler(CommandHandler("sclaiminfo", sclaiminfo_cmd, block=False))
application.add_handler(CommandHandler("resetsclaim", resetsclaim_cmd, block=False))

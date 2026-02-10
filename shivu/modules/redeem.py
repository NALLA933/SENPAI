"""
Redeem Module
Handles redeem codes for rewards.
"""

import time
import random
import string
from html import escape
from typing import Dict, Optional
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, user_collection, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import RARITY_MAP, to_small_caps

# In-memory redeem codes storage (can be moved to database)
redeem_codes: Dict[str, Dict] = {}
user_redeem_history: Dict[int, list] = {}

# Redeem cooldown
REDEEM_COOLDOWN_SECONDS = 60


def generate_code(length: int = 10) -> str:
    """Generate a random redeem code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


async def redeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/redeem <code> - Redeem a code for rewards."""
    user_id = update.effective_user.id
    
    # Check cooldown
    now = time.time()
    if user_id in user_redeem_history:
        last_redeem = user_redeem_history[user_id][-1] if user_redeem_history[user_id] else 0
        if now - last_redeem < REDEEM_COOLDOWN_SECONDS:
            remaining = int(REDEEM_COOLDOWN_SECONDS - (now - last_redeem))
            await update.message.reply_text(
                to_small_caps(f"⏱️ Please wait {remaining} seconds before redeeming again.")
            )
            return
    
    if not context.args:
        await update.message.reply_text(
            to_small_caps("Usage: /redeem <code>\n"
                         "Example: /redeem ABC123XYZ")
        )
        return
    
    code = context.args[0].upper().strip()
    
    # Check if code exists
    if code not in redeem_codes:
        await update.message.reply_text(to_small_caps("❌ Invalid or expired redeem code."))
        return
    
    code_data = redeem_codes[code]
    
    # Check if code is expired
    if code_data.get('expires'):
        if datetime.now() > code_data['expires']:
            del redeem_codes[code]
            await update.message.reply_text(to_small_caps("❌ This redeem code has expired."))
            return
    
    # Check if user already redeemed this code
    if user_id in code_data.get('redeemed_by', []):
        await update.message.reply_text(to_small_caps("❌ You have already redeemed this code."))
        return
    
    # Check max uses
    if code_data.get('max_uses'):
        if len(code_data.get('redeemed_by', [])) >= code_data['max_uses']:
            await update.message.reply_text(to_small_caps("❌ This code has reached its maximum uses."))
            return
    
    # Process redemption
    reward_type = code_data.get('reward_type', 'coins')
    reward_amount = code_data.get('reward_amount', 0)
    
    try:
        if reward_type == 'coins':
            await user_collection.update_one(
                {'id': user_id},
                {'$inc': {'balance': reward_amount}},
                upsert=True
            )
            
            reward_message = f"💰 {reward_amount:,} coins"
            
        elif reward_type == 'character':
            # This would need the character data
            await update.message.reply_text(to_small_caps("❌ Character rewards not implemented yet."))
            return
        else:
            await update.message.reply_text(to_small_caps("❌ Unknown reward type."))
            return
        
        # Mark code as redeemed by this user
        if 'redeemed_by' not in code_data:
            code_data['redeemed_by'] = []
        code_data['redeemed_by'].append(user_id)
        
        # Track user redeem history
        if user_id not in user_redeem_history:
            user_redeem_history[user_id] = []
        user_redeem_history[user_id].append(now)
        
        # Success message
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Redeem Successful!')}</b>\n\n"
            f"🎁 {to_small_caps('You received:')} {reward_message}\n\n"
            f"{to_small_caps('Thank you for using our bot!')}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"User {user_id} redeemed code {code} for {reward_amount} {reward_type}")
        
    except Exception as e:
        LOGGER.error(f"Error processing redeem: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing redeem. Please try again."))


async def createcode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/createcode <coins> [uses] [days_valid] - Create a redeem code (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if not context.args:
        await update.message.reply_text(
            to_small_caps("Usage: /createcode <coins> [uses] [days_valid]\n"
                         "Example: /createcode 1000 10 7")
        )
        return
    
    try:
        coins = int(context.args[0])
        if coins <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Coins must be a positive number."))
        return
    
    max_uses = None
    if len(context.args) > 1:
        try:
            max_uses = int(context.args[1])
            if max_uses <= 0:
                max_uses = None
        except ValueError:
            pass
    
    days_valid = None
    if len(context.args) > 2:
        try:
            days_valid = int(context.args[2])
            if days_valid <= 0:
                days_valid = None
        except ValueError:
            pass
    
    # Generate code
    code = generate_code()
    
    # Store code data
    redeem_codes[code] = {
        'reward_type': 'coins',
        'reward_amount': coins,
        'max_uses': max_uses,
        'expires': datetime.now() + timedelta(days=days_valid) if days_valid else None,
        'created_by': user_id,
        'created_at': datetime.now(),
        'redeemed_by': []
    }
    
    # Format message
    message = (
        f"✅ <b>{to_small_caps('Redeem Code Created!')}</b>\n\n"
        f"🎫 <code>{code}</code>\n\n"
        f"💰 {to_small_caps('Reward:')} {coins:,} coins\n"
    )
    
    if max_uses:
        message += f"👥 {to_small_caps('Max Uses:')} {max_uses}\n"
    else:
        message += f"👥 {to_small_caps('Max Uses:')} Unlimited\n"
    
    if days_valid:
        message += f"⏰ {to_small_caps('Valid for:')} {days_valid} days\n"
    else:
        message += f"⏰ {to_small_caps('Valid for:')} Forever\n"
    
    await update.message.reply_text(message, parse_mode='HTML')
    
    LOGGER.info(f"Admin {user_id} created redeem code {code} for {coins} coins")


async def listcodes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/listcodes - List all active redeem codes (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if not redeem_codes:
        await update.message.reply_text(to_small_caps("No active redeem codes."))
        return
    
    message = f"<b>{to_small_caps('🎫 Active Redeem Codes')}</b>\n\n"
    
    for code, data in redeem_codes.items():
        coins = data.get('reward_amount', 0)
        uses = len(data.get('redeemed_by', []))
        max_uses = data.get('max_uses', '∞')
        
        message += f"<code>{code}</code> - {coins:,} coins ({uses}/{max_uses} uses)\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def deletecode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/deletecode <code> - Delete a redeem code (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /deletecode <code>"))
        return
    
    code = context.args[0].upper().strip()
    
    if code not in redeem_codes:
        await update.message.reply_text(to_small_caps("❌ Code not found."))
        return
    
    del redeem_codes[code]
    await update.message.reply_text(to_small_caps(f"✅ Code {code} deleted successfully."))
    
    LOGGER.info(f"Admin {user_id} deleted redeem code {code}")


# Register handlers
application.add_handler(CommandHandler("redeem", redeem_cmd, block=False))
application.add_handler(CommandHandler("createcode", createcode_cmd, block=False))
application.add_handler(CommandHandler("listcodes", listcodes_cmd, block=False))
application.add_handler(CommandHandler("deletecode", deletecode_cmd, block=False))

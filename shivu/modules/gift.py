"""
Gift Module
Handles gifting characters between users.
"""

import time
from html import escape
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, user_collection, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity

# In-memory gift cooldowns
gift_cooldowns: Dict[int, float] = {}
GIFT_COOLDOWN_SECONDS = 300  # 5 minutes


async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gift <character_id> <@username|user_id> - Gift a character to another user."""
    sender_id = update.effective_user.id
    
    # Check cooldown
    now = time.time()
    if sender_id in gift_cooldowns:
        remaining = int(gift_cooldowns[sender_id] - now)
        if remaining > 0:
            await update.message.reply_text(
                to_small_caps(f"⏱️ Please wait {remaining} seconds before gifting again.")
            )
            return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            to_small_caps("Usage: /gift <character_id> <@username|user_id>\n"
                         "Example: /gift 123 @username")
        )
        return
    
    # Parse character ID
    try:
        char_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Character ID must be a number."))
        return
    
    # Parse recipient
    recipient_arg = context.args[1]
    recipient_id: Optional[int] = None
    
    if recipient_arg.startswith("@"):
        try:
            recipient = await context.bot.get_chat(recipient_arg)
            recipient_id = recipient.id
        except Exception:
            await update.message.reply_text(to_small_caps("❌ Could not find that user."))
            return
    elif recipient_arg.isdigit():
        recipient_id = int(recipient_arg)
    else:
        await update.message.reply_text(to_small_caps("❌ Invalid recipient. Use @username or user ID."))
        return
    
    if recipient_id == sender_id:
        await update.message.reply_text(to_small_caps("❌ You can't gift to yourself!"))
        return
    
    # Get sender's collection
    try:
        sender = await user_collection.find_one({'id': sender_id})
    except Exception as e:
        LOGGER.error(f"Error fetching sender: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing gift. Please try again."))
        return
    
    if not sender or not sender.get('characters'):
        await update.message.reply_text(to_small_caps("❌ You don't have any characters to gift!"))
        return
    
    # Find the character
    characters = sender.get('characters', [])
    character = None
    char_index = -1
    
    for i, char in enumerate(characters):
        if char.get('id') == char_id:
            character = char
            char_index = i
            break
    
    if not character:
        await update.message.reply_text(to_small_caps("❌ You don't have that character in your collection!"))
        return
    
    # Get recipient info
    try:
        recipient_chat = await context.bot.get_chat(recipient_id)
        recipient_name = escape(recipient_chat.first_name)
    except Exception:
        recipient_name = str(recipient_id)
    
    # Create confirmation message
    char_name = escape(character.get('name', 'Unknown'))
    anime_name = escape(character.get('anime', 'Unknown'))
    rarity = parse_rarity(character.get('rarity'))
    rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
    
    message = (
        f"<b>{to_small_caps('🎁 Gift Confirmation')}</b>\n\n"
        f"{to_small_caps('You are about to gift:')}\n"
        f"👤 {char_name}\n"
        f"🎬 {anime_name}\n"
        f"✨ {rarity_display}\n\n"
        f"{to_small_caps('To:')} <a href='tg://user?id={recipient_id}'>{recipient_name}</a>\n\n"
        f"{to_small_caps('This action cannot be undone!')}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"gift_confirm:{sender_id}:{recipient_id}:{char_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"gift_cancel:{sender_id}")
        ]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode='HTML')


async def gift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gift confirmation/cancellation."""
    query = update.callback_query
    data = query.data
    
    if data.startswith("gift_confirm:"):
        parts = data.split(":")
        if len(parts) != 4:
            await query.answer(to_small_caps("Invalid gift data"), show_alert=True)
            return
        
        _, sender_id, recipient_id, char_id = parts
        sender_id = int(sender_id)
        recipient_id = int(recipient_id)
        char_id = int(char_id)
        
        # Verify the user clicking is the sender
        if query.from_user.id != sender_id:
            await query.answer(to_small_caps("Only the sender can confirm this gift!"), show_alert=True)
            return
        
        await query.answer()
        
        # Process the gift
        try:
            # Get sender's data
            sender = await user_collection.find_one({'id': sender_id})
            if not sender:
                await query.edit_message_text(to_small_caps("❌ Error: Sender not found."))
                return
            
            # Find and remove character from sender
            characters = sender.get('characters', [])
            character = None
            
            for char in characters:
                if char.get('id') == char_id:
                    character = char
                    break
            
            if not character:
                await query.edit_message_text(to_small_caps("❌ Error: Character not found in your collection."))
                return
            
            # Remove from sender
            await user_collection.update_one(
                {'id': sender_id},
                {'$pull': {'characters': {'id': char_id}}}
            )
            
            # Add to recipient
            await user_collection.update_one(
                {'id': recipient_id},
                {'$push': {'characters': character}},
                upsert=True
            )
            
            # Set cooldown
            gift_cooldowns[sender_id] = time.time() + GIFT_COOLDOWN_SECONDS
            
            # Get names
            sender_name = escape(query.from_user.first_name)
            try:
                recipient_chat = await context.bot.get_chat(recipient_id)
                recipient_name = escape(recipient_chat.first_name)
            except Exception:
                recipient_name = str(recipient_id)
            
            char_name = escape(character.get('name', 'Unknown'))
            rarity = parse_rarity(character.get('rarity'))
            rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
            
            await query.edit_message_text(
                f"✅ <b>{to_small_caps('Gift Successful!')}</b>\n\n"
                f"<a href='tg://user?id={sender_id}'>{sender_name}</a> {to_small_caps('gifted')}\n"
                f"👤 {char_name} ({rarity_display})\n"
                f"{to_small_caps('to')} <a href='tg://user?id={recipient_id}'>{recipient_name}</a>\n\n"
                f"{to_small_caps('Next gift available in')} {GIFT_COOLDOWN_SECONDS // 60} {to_small_caps('minutes')}",
                parse_mode='HTML'
            )
            
            LOGGER.info(f"User {sender_id} gifted character {char_id} to {recipient_id}")
            
        except Exception as e:
            LOGGER.error(f"Error processing gift: {e}")
            await query.edit_message_text(to_small_caps("❌ Error processing gift. Please try again."))
    
    elif data.startswith("gift_cancel:"):
        sender_id = int(data.split(":")[1])
        
        if query.from_user.id != sender_id:
            await query.answer(to_small_caps("Only the sender can cancel this gift!"), show_alert=True)
            return
        
        await query.answer()
        await query.edit_message_text(to_small_caps("❌ Gift cancelled."))


async def giftall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/giftall <@username|user_id> - Gift all characters to another user (Owner only)."""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /giftall <@username|user_id>"))
        return
    
    # Parse recipient
    recipient_arg = context.args[0]
    recipient_id: Optional[int] = None
    
    if recipient_arg.startswith("@"):
        try:
            recipient = await context.bot.get_chat(recipient_arg)
            recipient_id = recipient.id
        except Exception:
            await update.message.reply_text(to_small_caps("❌ Could not find that user."))
            return
    elif recipient_arg.isdigit():
        recipient_id = int(recipient_arg)
    else:
        await update.message.reply_text(to_small_caps("❌ Invalid recipient. Use @username or user ID."))
        return
    
    # Get sender's collection
    try:
        sender = await user_collection.find_one({'id': user_id})
    except Exception as e:
        LOGGER.error(f"Error fetching sender: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing gift. Please try again."))
        return
    
    if not sender or not sender.get('characters'):
        await update.message.reply_text(to_small_caps("❌ You don't have any characters to gift!"))
        return
    
    characters = sender.get('characters', [])
    
    # Transfer all characters
    try:
        # Add all to recipient
        await user_collection.update_one(
            {'id': recipient_id},
            {'$push': {'characters': {'$each': characters}}},
            upsert=True
        )
        
        # Clear sender's collection
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'characters': []}}
        )
        
        # Get recipient name
        try:
            recipient_chat = await context.bot.get_chat(recipient_id)
            recipient_name = escape(recipient_chat.first_name)
        except Exception:
            recipient_name = str(recipient_id)
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Gift All Successful!')}</b>\n\n"
            f"{len(characters)} {to_small_caps('characters gifted to')} "
            f"<a href='tg://user?id={recipient_id}'>{recipient_name}</a>",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"User {user_id} gifted all {len(characters)} characters to {recipient_id}")
        
    except Exception as e:
        LOGGER.error(f"Error processing giftall: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing gift. Please try again."))


# Register handlers
application.add_handler(CommandHandler("gift", gift_cmd, block=False))
application.add_handler(CommandHandler("giftall", giftall_cmd, block=False))
application.add_handler(CallbackQueryHandler(gift_callback, pattern=r"^gift_", block=False))

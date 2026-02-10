"""
Give Module
Admin command to give characters directly to users.
"""

from html import escape
from typing import Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, collection, user_collection, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity


async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/give <character_id> <@username|user_id> - Give a character to a user (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            to_small_caps("Usage: /give <character_id> <@username|user_id>\n"
                         "Example: /give 123 @username")
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
    
    # Get character from database
    try:
        character = await collection.find_one({'id': char_id})
    except Exception as e:
        LOGGER.error(f"Error fetching character: {e}")
        await update.message.reply_text(to_small_caps("❌ Error fetching character. Please try again."))
        return
    
    if not character:
        await update.message.reply_text(to_small_caps("❌ Character not found in database!"))
        return
    
    # Add character to recipient
    try:
        char_to_add = {
            'id': character.get('id'),
            'name': character.get('name'),
            'anime': character.get('anime'),
            'rarity': character.get('rarity'),
            'img_url': character.get('img_url')
        }
        
        await user_collection.update_one(
            {'id': recipient_id},
            {'$push': {'characters': char_to_add}},
            upsert=True
        )
        
        # Get names
        try:
            recipient_chat = await context.bot.get_chat(recipient_id)
            recipient_name = escape(recipient_chat.first_name)
        except Exception:
            recipient_name = str(recipient_id)
        
        char_name = escape(character.get('name', 'Unknown'))
        anime_name = escape(character.get('anime', 'Unknown'))
        rarity = parse_rarity(character.get('rarity'))
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Character Given Successfully!')}</b>\n\n"
            f"👤 {char_name}\n"
            f"🎬 {anime_name}\n"
            f"✨ {rarity_display}\n"
            f"🆔 ID: <code>{char_id}</code>\n\n"
            f"{to_small_caps('Given to:')} <a href='tg://user?id={recipient_id}'>{recipient_name}</a>",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Admin {user_id} gave character {char_id} to user {recipient_id}")
        
    except Exception as e:
        LOGGER.error(f"Error giving character: {e}")
        await update.message.reply_text(to_small_caps("❌ Error giving character. Please try again."))


async def givecoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/givecoins <amount> <@username|user_id> - Give coins to a user (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            to_small_caps("Usage: /givecoins <amount> <@username|user_id>\n"
                         "Example: /givecoins 1000 @username")
        )
        return
    
    # Parse amount
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Amount must be a positive number."))
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
    
    # Add coins to recipient
    try:
        await user_collection.update_one(
            {'id': recipient_id},
            {'$inc': {'balance': amount}},
            upsert=True
        )
        
        # Get recipient name
        try:
            recipient_chat = await context.bot.get_chat(recipient_id)
            recipient_name = escape(recipient_chat.first_name)
        except Exception:
            recipient_name = str(recipient_id)
        
        # Get new balance
        user = await user_collection.find_one({'id': recipient_id})
        new_balance = user.get('balance', 0) if user else amount
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Coins Given Successfully!')}</b>\n\n"
            f"💰 +{amount:,} coins\n"
            f"{to_small_caps('Given to:')} <a href='tg://user?id={recipient_id}'>{recipient_name}</a>\n"
            f"{to_small_caps('New Balance:')} {new_balance:,} coins",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Admin {user_id} gave {amount} coins to user {recipient_id}")
        
    except Exception as e:
        LOGGER.error(f"Error giving coins: {e}")
        await update.message.reply_text(to_small_caps("❌ Error giving coins. Please try again."))


# Register handlers
application.add_handler(CommandHandler("give", give_cmd, block=False))
application.add_handler(CommandHandler("givecoins", givecoins_cmd, block=False))

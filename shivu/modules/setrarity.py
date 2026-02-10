"""
Rarity and Character Lock Management Module
Handles disabling/enabling rarities for chats and locking/unlocking characters globally.
"""

import logging
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, db, OWNER_ID, SUDO_USERS
from shivu.utils import RARITY_MAP, to_small_caps

LOGGER = logging.getLogger(__name__)

# Collections
disabled_rarities_collection = db.disabled_rarities
locked_characters_collection = db.locked_characters


# ============ DATABASE FUNCTIONS ============

async def get_disabled_rarities(chat_id: int) -> List[int]:
    """Get list of disabled rarities for a chat."""
    try:
        doc = await disabled_rarities_collection.find_one({"chat_id": chat_id})
        if doc:
            return doc.get("rarities", [])
        return []
    except Exception as e:
        LOGGER.error(f"Error getting disabled rarities: {e}")
        return []


async def set_rarity_disabled(chat_id: int, rarity: int, disabled: bool = True):
    """Enable or disable a rarity for a chat."""
    try:
        if disabled:
            await disabled_rarities_collection.update_one(
                {"chat_id": chat_id},
                {"$addToSet": {"rarities": rarity}},
                upsert=True
            )
        else:
            await disabled_rarities_collection.update_one(
                {"chat_id": chat_id},
                {"$pull": {"rarities": rarity}}
            )
        return True
    except Exception as e:
        LOGGER.error(f"Error setting rarity disabled: {e}")
        return False


async def get_locked_character_ids() -> List[str]:
    """Get list of globally locked character IDs."""
    try:
        locked = []
        async for doc in locked_characters_collection.find({}):
            locked.append(str(doc.get("character_id")))
        return locked
    except Exception as e:
        LOGGER.error(f"Error getting locked characters: {e}")
        return []


async def is_character_locked(character_id) -> bool:
    """Check if a character is globally locked."""
    try:
        doc = await locked_characters_collection.find_one({"character_id": str(character_id)})
        return doc is not None
    except Exception as e:
        LOGGER.error(f"Error checking locked character: {e}")
        return False


async def lock_character(character_id, locked_by: int, reason: str = ""):
    """Globally lock a character."""
    try:
        await locked_characters_collection.update_one(
            {"character_id": str(character_id)},
            {
                "$set": {
                    "character_id": str(character_id),
                    "locked_by": locked_by,
                    "reason": reason
                }
            },
            upsert=True
        )
        return True
    except Exception as e:
        LOGGER.error(f"Error locking character: {e}")
        return False


async def unlock_character(character_id):
    """Unlock a globally locked character."""
    try:
        result = await locked_characters_collection.delete_one({"character_id": str(character_id)})
        return result.deleted_count > 0
    except Exception as e:
        LOGGER.error(f"Error unlocking character: {e}")
        return False


# ============ COMMAND HANDLERS ============

async def setrarity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setrarity - Manage rarity settings for this chat (Admin only)"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if user is admin in the chat
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            if user_id != OWNER_ID and user_id not in SUDO_USERS:
                await update.message.reply_text("❌ Only chat admins can use this command.")
                return
    except Exception as e:
        LOGGER.error(f"Error checking admin status: {e}")
        return
    
    # Get current disabled rarities
    disabled = await get_disabled_rarities(chat_id)
    
    # Create keyboard
    keyboard = []
    row = []
    
    for rarity_num, rarity_name in RARITY_MAP.items():
        is_disabled = rarity_num in disabled
        status = "❌" if is_disabled else "✅"
        btn_text = f"{status} {rarity_name}"
        callback_data = f"setrarity_{rarity_num}_{'enable' if is_disabled else 'disable'}"
        
        row.append(InlineKeyboardButton(
            to_small_caps(btn_text),
            callback_data=callback_data
        ))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(
        to_small_caps("❌ Close"),
        callback_data="setrarity_close"
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"<b>⚙️ {to_small_caps('Rarity Settings')}</b>\n\n"
        f"{to_small_caps('Click on a rarity to toggle it.')}\n"
        f"{to_small_caps('✅ = Enabled (characters will appear)')}\n"
        f"{to_small_caps('❌ = Disabled (characters will NOT appear)')}\n\n"
        f"{to_small_caps('Currently disabled:')} {len(disabled)}"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def lockchar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/lockchar <character_id> - Globally lock a character (Owner/Sudo only)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            f"<b>🔒 {to_small_caps('Lock Character')}</b>\n\n"
            f"{to_small_caps('Usage:')} <code>/lockchar &lt;character_id&gt;</code>\n"
            f"{to_small_caps('Example:')} <code>/lockchar 123</code>",
            parse_mode='HTML'
        )
        return
    
    character_id = context.args[0]
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    success = await lock_character(character_id, user_id, reason)
    
    if success:
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Character Locked')}</b>\n\n"
            f"🆔 {to_small_caps('ID:')} <code>{character_id}</code>\n"
            f"📝 {to_small_caps('Reason:')} {reason}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Failed to lock character.")


async def unlockchar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unlockchar <character_id> - Globally unlock a character (Owner/Sudo only)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            f"<b>🔓 {to_small_caps('Unlock Character')}</b>\n\n"
            f"{to_small_caps('Usage:')} <code>/unlockchar &lt;character_id&gt;</code>",
            parse_mode='HTML'
        )
        return
    
    character_id = context.args[0]
    
    success = await unlock_character(character_id)
    
    if success:
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Character Unlocked')}</b>\n\n"
            f"🆔 {to_small_caps('ID:')} <code>{character_id}</code>\n"
            f"{to_small_caps('This character can now appear in chats.')}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"❌ {to_small_caps('Character not found in locked list or already unlocked.')}")


async def lockedchars_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/lockedchars - List all globally locked characters (Owner/Sudo only)"""
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    locked = await get_locked_character_ids()
    
    if not locked:
        await update.message.reply_text(f"✅ {to_small_caps('No characters are currently locked.')}")
        return
    
    message = f"<b>🔒 {to_small_caps('Locked Characters')}</b>\n\n"
    message += f"{to_small_caps('Total:')} {len(locked)}\n\n"
    
    for i, char_id in enumerate(locked[:50], 1):  # Limit to 50
        message += f"{i}. <code>{char_id}</code>\n"
    
    if len(locked) > 50:
        message += f"\n... {to_small_caps('and')} {len(locked) - 50} {to_small_caps('more')}"
    
    await update.message.reply_text(message, parse_mode='HTML')


# ============ CALLBACK HANDLERS ============

async def setrarity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rarity toggle callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "setrarity_close":
        await query.message.delete()
        return
    
    parts = data.split("_")
    if len(parts) != 3:
        return
    
    _, rarity_str, action = parts
    rarity = int(rarity_str)
    chat_id = query.message.chat.id
    
    # Toggle the rarity
    if action == "disable":
        await set_rarity_disabled(chat_id, rarity, True)
    else:
        await set_rarity_disabled(chat_id, rarity, False)
    
    # Refresh the menu
    disabled = await get_disabled_rarities(chat_id)
    
    keyboard = []
    row = []
    
    for rarity_num, rarity_name in RARITY_MAP.items():
        is_disabled = rarity_num in disabled
        status = "❌" if is_disabled else "✅"
        btn_text = f"{status} {rarity_name}"
        callback_data = f"setrarity_{rarity_num}_{'enable' if is_disabled else 'disable'}"
        
        row.append(InlineKeyboardButton(
            to_small_caps(btn_text),
            callback_data=callback_data
        ))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(
        to_small_caps("❌ Close"),
        callback_data="setrarity_close"
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"<b>⚙️ {to_small_caps('Rarity Settings')}</b>\n\n"
        f"{to_small_caps('Click on a rarity to toggle it.')}\n"
        f"{to_small_caps('✅ = Enabled (characters will appear)')}\n"
        f"{to_small_caps('❌ = Disabled (characters will NOT appear)')}\n\n"
        f"{to_small_caps('Currently disabled:')} {len(disabled)}"
    )
    
    try:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        LOGGER.error(f"Error updating rarity menu: {e}")


# ============ SETUP FUNCTION ============

def setup_handlers():
    """Register all handlers for this module"""
    application.add_handler(CommandHandler("setrarity", setrarity_command, block=False))
    application.add_handler(CommandHandler("lockchar", lockchar_command, block=False))
    application.add_handler(CommandHandler("unlockchar", unlockchar_command, block=False))
    application.add_handler(CommandHandler("lockedchars", lockedchars_command, block=False))
    application.add_handler(CallbackQueryHandler(setrarity_callback, pattern="^setrarity_", block=False))
    LOGGER.info("Setrarity module handlers registered")


# Auto-register on import
setup_handlers()

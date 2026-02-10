"""
Sort Mode Module
Handles rarity filtering for harem display.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from shivu import application, LOGGER
from shivu.utils import RARITY_MAP, to_small_caps

# In-memory user preferences (can be moved to database for persistence)
user_sort_preferences: dict = {}


async def get_user_sort_preference(user_id: int) -> int | None:
    """Get user's current rarity filter preference."""
    return user_sort_preferences.get(user_id)


async def set_user_sort_preference(user_id: int, rarity: int | None):
    """Set user's rarity filter preference."""
    if rarity is None:
        user_sort_preferences.pop(user_id, None)
    else:
        user_sort_preferences[user_id] = rarity


def build_smode_keyboard(user_id: int, current_filter: int | None) -> InlineKeyboardMarkup:
    """Build the sort mode keyboard."""
    keyboard = []
    
    # Show current filter status
    if current_filter:
        current_name = RARITY_MAP.get(current_filter, "Unknown")
        keyboard.append([InlineKeyboardButton(
            to_small_caps(f"Current: {current_name}"),
            callback_data="smode_status"
        )])
    
    # Rarity buttons - 2 per row
    row = []
    for rarity_num, rarity_name in RARITY_MAP.items():
        is_selected = current_filter == rarity_num
        
        if is_selected:
            btn_text = f"✅ {rarity_name}"
            callback = f"smode_clear:{user_id}"
        else:
            btn_text = rarity_name
            callback = f"smode_set:{rarity_num}:{user_id}"
        
        row.append(InlineKeyboardButton(
            to_small_caps(btn_text),
            callback_data=callback
        ))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Clear filter button
    if current_filter:
        keyboard.append([InlineKeyboardButton(
            to_small_caps("🗑️ Clear Filter"),
            callback_data=f"smode_clear:{user_id}"
        )])
    
    # Close button
    keyboard.append([InlineKeyboardButton(
        to_small_caps("❌ Close"),
        callback_data=f"smode_close:{user_id}"
    )])
    
    return InlineKeyboardMarkup(keyboard)


async def smode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/smode - Open sort mode menu to filter harem by rarity."""
    user_id = update.effective_user.id
    current_filter = await get_user_sort_preference(user_id)
    
    keyboard = build_smode_keyboard(user_id, current_filter)
    
    if current_filter:
        filter_name = RARITY_MAP.get(current_filter, "Unknown")
        message = (
            f"<b>{to_small_caps('🎴 Sort Mode')}</b>\n\n"
            f"{to_small_caps('Current filter:')} <b>{filter_name}</b>\n\n"
            f"{to_small_caps('Click on a rarity to filter your harem:')}"
        )
    else:
        message = (
            f"<b>{to_small_caps('🎴 Sort Mode')}</b>\n\n"
            f"{to_small_caps('No filter active. Showing all rarities.')}"
        )
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode='HTML')


async def smode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle smode callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("smode_set:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        
        _, rarity_str, user_id_str = parts
        rarity = int(rarity_str)
        user_id = int(user_id_str)
        
        if query.from_user.id != user_id:
            await query.answer(to_small_caps("This menu is not for you!"), show_alert=True)
            return
        
        await set_user_sort_preference(user_id, rarity)
        
        # Update keyboard
        keyboard = build_smode_keyboard(user_id, rarity)
        filter_name = RARITY_MAP.get(rarity, "Unknown")
        
        message = (
            f"<b>{to_small_caps('🎴 Sort Mode')}</b>\n\n"
            f"{to_small_caps('Filter set to:')} <b>{filter_name}</b>\n\n"
            f"{to_small_caps('Use /harem to see filtered results.')}\n"
            f"{to_small_caps('Click the same rarity to remove filter.')}."
        )
        
        try:
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            LOGGER.error(f"Error updating smode message: {e}")
    
    elif data.startswith("smode_clear:"):
        parts = data.split(":")
        if len(parts) != 2:
            return
        
        _, user_id_str = parts
        user_id = int(user_id_str)
        
        if query.from_user.id != user_id:
            await query.answer(to_small_caps("This menu is not for you!"), show_alert=True)
            return
        
        await set_user_sort_preference(user_id, None)
        
        # Update keyboard
        keyboard = build_smode_keyboard(user_id, None)
        
        message = (
            f"<b>{to_small_caps('🎴 Sort Mode')}</b>\n\n"
            f"{to_small_caps('Filter cleared. Showing all rarities.')}\n\n"
            f"{to_small_caps('Click on a rarity to filter your harem:')}"
        )
        
        try:
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            LOGGER.error(f"Error updating smode message: {e}")
    
    elif data.startswith("smode_close:"):
        parts = data.split(":")
        if len(parts) != 2:
            return
        
        _, user_id_str = parts
        user_id = int(user_id_str)
        
        if query.from_user.id != user_id:
            await query.answer(to_small_caps("This menu is not for you!"), show_alert=True)
            return
        
        try:
            await query.message.delete()
        except Exception as e:
            LOGGER.error(f"Error deleting smode message: {e}")
    
    elif data == "smode_status":
        await query.answer(to_small_caps("Current filter status"), show_alert=False)


# Register handlers
application.add_handler(CommandHandler("smode", smode_cmd, block=False))
application.add_handler(CallbackQueryHandler(smode_callback, pattern=r"^smode_", block=False))

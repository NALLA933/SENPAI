"""
Shop Module
Handles the character shop where users can buy characters with coins.
"""

import random
import time
from typing import Dict, List, Optional
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, collection, user_collection, LOGGER
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity

# Shop configuration
SHOP_REFRESH_INTERVAL = 3600  # 1 hour
MAX_SHOP_ITEMS = 10

# In-memory shop cache
shop_cache: Dict[int, Dict] = {}


async def get_shop_items(chat_id: int) -> List[Dict]:
    """Get or generate shop items for a chat."""
    now = time.time()
    
    if chat_id in shop_cache:
        cache = shop_cache[chat_id]
        if now - cache['timestamp'] < SHOP_REFRESH_INTERVAL:
            return cache['items']
    
    # Generate new shop items
    try:
        # Get random characters from database
        pipeline = [
            {"$sample": {"size": MAX_SHOP_ITEMS * 2}}  # Get more to filter
        ]
        
        cursor = collection.aggregate(pipeline)
        all_chars = await cursor.to_list(length=MAX_SHOP_ITEMS * 2)
        
        items = []
        seen_ids = set()
        
        for char in all_chars:
            char_id = char.get('id')
            if char_id in seen_ids:
                continue
            
            seen_ids.add(char_id)
            
            # Calculate price based on rarity
            rarity = parse_rarity(char.get('rarity'))
            base_price = rarity * 1000
            variation = random.randint(-200, 200)
            price = max(100, base_price + variation)
            
            items.append({
                'character': char,
                'price': price,
                'rarity': rarity
            })
            
            if len(items) >= MAX_SHOP_ITEMS:
                break
        
        # Cache the items
        shop_cache[chat_id] = {
            'items': items,
            'timestamp': now
        }
        
        return items
        
    except Exception as e:
        LOGGER.error(f"Error generating shop items: {e}")
        return []


async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shop - Display the character shop."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    items = await get_shop_items(chat_id)
    
    if not items:
        await update.message.reply_text(to_small_caps("❌ Shop is temporarily unavailable. Please try again later."))
        return
    
    # Get user balance
    try:
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0) if user else 0
    except Exception as e:
        LOGGER.error(f"Error getting user balance: {e}")
        balance = 0
    
    message = f"<b>{to_small_caps('🏪 Character Shop')}</b>\n\n"
    message += f"{to_small_caps('Your Balance:')} <b>{balance:,}</b> coins\n"
    message += f"{to_small_caps('Use /buy <item_number> to purchase')}\n\n"
    
    for i, item in enumerate(items, 1):
        char = item['character']
        price = item['price']
        rarity = item['rarity']
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        can_afford = balance >= price
        status = "✅" if can_afford else "❌"
        
        message += (
            f"{status} <b>#{i}</b>\n"
            f"👤 {to_small_caps(escape(char.get('name', 'Unknown')))}\n"
            f"🎬 {to_small_caps(escape(char.get('anime', 'Unknown')))}\n"
            f"✨ {rarity_display}\n"
            f"💰 <b>{price:,}</b> coins\n"
            f"🆔 ID: <code>{char.get('id')}</code>\n\n"
        )
    
    # Create refresh button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(to_small_caps("🔄 Refresh Shop"), callback_data=f"shop_refresh:{chat_id}")]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode='HTML')


async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/buy <item_number> - Buy a character from the shop."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /buy <item_number>\nExample: /buy 1"))
        return
    
    try:
        item_num = int(context.args[0])
        if item_num < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Please enter a valid item number."))
        return
    
    items = await get_shop_items(chat_id)
    
    if not items or item_num > len(items):
        await update.message.reply_text(to_small_caps("❌ Invalid item number. Use /shop to see available items."))
        return
    
    item = items[item_num - 1]
    char = item['character']
    price = item['price']
    
    # Get user balance
    try:
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0) if user else 0
    except Exception as e:
        LOGGER.error(f"Error getting user balance: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing purchase. Please try again."))
        return
    
    if balance < price:
        await update.message.reply_text(
            to_small_caps(f"❌ Insufficient balance!\n\n"
                         f"Price: {price:,} coins\n"
                         f"Your balance: {balance:,} coins\n"
                         f"Need: {price - balance:,} more coins")
        )
        return
    
    # Process purchase
    try:
        # Deduct balance
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'balance': -price}}
        )
        
        # Add character to collection
        char_to_add = {
            'id': char.get('id'),
            'name': char.get('name'),
            'anime': char.get('anime'),
            'rarity': char.get('rarity'),
            'img_url': char.get('img_url')
        }
        
        await user_collection.update_one(
            {'id': user_id},
            {'$push': {'characters': char_to_add}},
            upsert=True
        )
        
        # Remove from shop
        shop_cache[chat_id]['items'].pop(item_num - 1)
        
        rarity_display = RARITY_MAP.get(parse_rarity(char.get('rarity')), '⚪ Common')
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Purchase Successful!')}</b>\n\n"
            f"👤 {to_small_caps(escape(char.get('name', 'Unknown')))}\n"
            f"🎬 {to_small_caps(escape(char.get('anime', 'Unknown')))}\n"
            f"✨ {rarity_display}\n"
            f"💰 -{price:,} coins\n\n"
            f"{to_small_caps('Character added to your harem!')}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"User {user_id} bought character {char.get('id')} for {price} coins")
        
    except Exception as e:
        LOGGER.error(f"Error processing purchase: {e}")
        await update.message.reply_text(to_small_caps("❌ Error processing purchase. Please try again."))


async def shop_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shop refresh callback."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("shop_refresh:"):
        return
    
    chat_id = int(data.split(":")[1])
    
    # Force refresh
    if chat_id in shop_cache:
        del shop_cache[chat_id]
    
    items = await get_shop_items(chat_id)
    
    if not items:
        await query.edit_message_text(to_small_caps("❌ Shop is temporarily unavailable. Please try again later."))
        return
    
    user_id = query.from_user.id
    
    # Get user balance
    try:
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0) if user else 0
    except Exception as e:
        LOGGER.error(f"Error getting user balance: {e}")
        balance = 0
    
    message = f"<b>{to_small_caps('🏪 Character Shop (Refreshed)')}</b>\n\n"
    message += f"{to_small_caps('Your Balance:')} <b>{balance:,}</b> coins\n"
    message += f"{to_small_caps('Use /buy <item_number> to purchase')}\n\n"
    
    for i, item in enumerate(items, 1):
        char = item['character']
        price = item['price']
        rarity = item['rarity']
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        can_afford = balance >= price
        status = "✅" if can_afford else "❌"
        
        message += (
            f"{status} <b>#{i}</b>\n"
            f"👤 {to_small_caps(escape(char.get('name', 'Unknown')))}\n"
            f"🎬 {to_small_caps(escape(char.get('anime', 'Unknown')))}\n"
            f"✨ {rarity_display}\n"
            f"💰 <b>{price:,}</b> coins\n"
            f"🆔 ID: <code>{char.get('id')}</code>\n\n"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(to_small_caps("🔄 Refresh Shop"), callback_data=f"shop_refresh:{chat_id}")]
    ])
    
    try:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='HTML')
    except Exception as e:
        LOGGER.error(f"Error updating shop message: {e}")


# Register handlers
application.add_handler(CommandHandler("shop", shop_cmd, block=False))
application.add_handler(CommandHandler("buy", buy_cmd, block=False))
application.add_handler(CallbackQueryHandler(shop_refresh_callback, pattern=r"^shop_refresh:", block=False))

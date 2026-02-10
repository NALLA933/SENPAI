"""
Inline Query Module
Handles inline queries for searching user's collection.
"""

import re
from html import escape
from typing import List, Dict, Any

from telegram import (
    Update, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import InlineQueryHandler, ContextTypes

from shivu import application, user_collection, collection, LOGGER
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries for user's collection."""
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    
    # Get user's collection
    try:
        user = await user_collection.find_one({'id': user_id})
    except Exception as e:
        LOGGER.error(f"Error fetching user for inline query: {e}")
        await update.inline_query.answer([], cache_time=0)
        return
    
    if not user or not user.get('characters'):
        await update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id="no_chars",
                    title=to_small_caps("No Characters"),
                    input_message_content=InputTextMessageContent(
                        to_small_caps("You haven't collected any characters yet! Use /guess to collect characters.")
                    )
                )
            ],
            cache_time=0
        )
        return
    
    characters = user.get('characters', [])
    
    # Filter by query if provided
    if query:
        regex = re.compile(query, re.IGNORECASE)
        filtered = [c for c in characters if regex.search(c.get('name', '')) or regex.search(c.get('anime', ''))]
    else:
        filtered = characters
    
    # Limit results
    filtered = filtered[:50]
    
    if not filtered:
        await update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id="no_match",
                    title=to_small_caps("No Matches"),
                    input_message_content=InputTextMessageContent(
                        to_small_caps(f"No characters found matching '{escape(query)}'.")
                    )
                )
            ],
            cache_time=0
        )
        return
    
    # Build results
    results = []
    for i, char in enumerate(filtered):
        char_id = char.get('id', f'unknown_{i}')
        name = escape(char.get('name', 'Unknown'))
        anime = escape(char.get('anime', 'Unknown'))
        rarity = parse_rarity(char.get('rarity'))
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        # Count duplicates
        count = sum(1 for c in characters if c.get('id') == char_id)
        
        message_text = (
            f"<b>{name}</b>\n"
            f"🎬 {anime}\n"
            f"✨ {rarity_display}\n"
            f"🆔 ID: <code>{char_id}</code>\n"
        )
        
        if count > 1:
            message_text += f"📦 x{count}\n"
        
        result = InlineQueryResultArticle(
            id=str(char_id),
            title=name,
            description=f"{anime} | {rarity_display}",
            input_message_content=InputTextMessageContent(
                message_text,
                parse_mode='HTML'
            ),
            thumb_url=char.get('img_url', '')
        )
        
        results.append(result)
    
    await update.inline_query.answer(results, cache_time=5)


async def collection_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle collection.* inline queries."""
    query = update.inline_query.query.strip()
    
    # Parse query format: collection.user_id
    if not query.startswith("collection."):
        return
    
    try:
        parts = query.split(".")
        if len(parts) < 2:
            return
        target_user_id = int(parts[1])
    except (ValueError, IndexError):
        await update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id="invalid",
                    title=to_small_caps("Invalid Query"),
                    input_message_content=InputTextMessageContent(
                        to_small_caps("Invalid collection query format.")
                    )
                )
            ],
            cache_time=0
        )
        return
    
    # Get target user's collection
    try:
        user = await user_collection.find_one({'id': target_user_id})
    except Exception as e:
        LOGGER.error(f"Error fetching user for collection query: {e}")
        await update.inline_query.answer([], cache_time=0)
        return
    
    if not user:
        await update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id="user_not_found",
                    title=to_small_caps("User Not Found"),
                    input_message_content=InputTextMessageContent(
                        to_small_caps("User not found in database.")
                    )
                )
            ],
            cache_time=0
        )
        return
    
    characters = user.get('characters', [])
    
    if not characters:
        await update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id="no_chars",
                    title=to_small_caps("No Characters"),
                    input_message_content=InputTextMessageContent(
                        to_small_caps("This user hasn't collected any characters yet.")
                    )
                )
            ],
            cache_time=0
        )
        return
    
    # Get user info
    try:
        target_user = await context.bot.get_chat(target_user_id)
        user_name = escape(target_user.first_name)
    except Exception:
        user_name = str(target_user_id)
    
    # Build results
    results = []
    seen_ids = set()
    
    for char in characters:
        char_id = char.get('id')
        if char_id in seen_ids:
            continue
        seen_ids.add(char_id)
        
        name = escape(char.get('name', 'Unknown'))
        anime = escape(char.get('anime', 'Unknown'))
        rarity = parse_rarity(char.get('rarity'))
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        # Count duplicates
        count = sum(1 for c in characters if c.get('id') == char_id)
        
        message_text = (
            f"<b>{user_name}'s Collection</b>\n\n"
            f"<b>{name}</b>\n"
            f"🎬 {anime}\n"
            f"✨ {rarity_display}\n"
            f"🆔 ID: <code>{char_id}</code>\n"
        )
        
        if count > 1:
            message_text += f"📦 x{count}\n"
        
        result = InlineQueryResultArticle(
            id=str(char_id),
            title=name,
            description=f"{anime} | {rarity_display}",
            input_message_content=InputTextMessageContent(
                message_text,
                parse_mode='HTML'
            ),
            thumb_url=char.get('img_url', '')
        )
        
        results.append(result)
        
        if len(results) >= 50:
            break
    
    await update.inline_query.answer(results, cache_time=5)


# Register handlers
application.add_handler(InlineQueryHandler(inline_query, block=False))

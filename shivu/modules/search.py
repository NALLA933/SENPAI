"""
Search Module
Handles searching for characters and anime.
"""

import re
from html import escape
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, collection, LOGGER
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity

# Maximum results per page
RESULTS_PER_PAGE = 10


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/search <query> - Search for characters by name."""
    if not context.args:
        await update.message.reply_text(
            to_small_caps("Usage: /search <character_name>\n"
                         "Example: /search naruto")
        )
        return
    
    query = " ".join(context.args).strip()
    
    if len(query) < 2:
        await update.message.reply_text(to_small_caps("❌ Please enter at least 2 characters to search."))
        return
    
    # Search in database
    try:
        # Case-insensitive regex search
        regex_query = re.compile(query, re.IGNORECASE)
        
        pipeline = [
            {"$match": {"name": {"$regex": regex_query}}},
            {"$limit": RESULTS_PER_PAGE}
        ]
        
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=RESULTS_PER_PAGE)
        
    except Exception as e:
        LOGGER.error(f"Error searching characters: {e}")
        await update.message.reply_text(to_small_caps("❌ Error searching. Please try again."))
        return
    
    if not results:
        await update.message.reply_text(
            to_small_caps(f"❌ No characters found matching '{escape(query)}'.")
        )
        return
    
    # Format results
    message = f"<b>{to_small_caps('🔍 Search Results')}</b>\n\n"
    message += f"{to_small_caps('Query:')} <code>{escape(query)}</code>\n"
    message += f"{to_small_caps('Found:')} {len(results)} {to_small_caps('characters')}\n\n"
    
    for i, char in enumerate(results, 1):
        name = escape(char.get('name', 'Unknown'))
        anime = escape(char.get('anime', 'Unknown'))
        rarity = parse_rarity(char.get('rarity'))
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        char_id = char.get('id', 'N/A')
        
        message += (
            f"{i}. <b>{name}</b>\n"
            f"   🎬 {anime}\n"
            f"   ✨ {rarity_display}\n"
            f"   🆔 ID: <code>{char_id}</code>\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='HTML')


async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/anime <anime_name> - Search for characters from a specific anime."""
    if not context.args:
        await update.message.reply_text(
            to_small_caps("Usage: /anime <anime_name>\n"
                         "Example: /anime naruto")
        )
        return
    
    query = " ".join(context.args).strip()
    
    if len(query) < 2:
        await update.message.reply_text(to_small_caps("❌ Please enter at least 2 characters to search."))
        return
    
    # Search in database
    try:
        # Case-insensitive regex search on anime field
        regex_query = re.compile(query, re.IGNORECASE)
        
        pipeline = [
            {"$match": {"anime": {"$regex": regex_query}}},
            {"$limit": RESULTS_PER_PAGE}
        ]
        
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=RESULTS_PER_PAGE)
        
    except Exception as e:
        LOGGER.error(f"Error searching anime: {e}")
        await update.message.reply_text(to_small_caps("❌ Error searching. Please try again."))
        return
    
    if not results:
        await update.message.reply_text(
            to_small_caps(f"❌ No characters found from anime matching '{escape(query)}'.")
        )
        return
    
    # Format results
    message = f"<b>{to_small_caps('🎬 Anime Search Results')}</b>\n\n"
    message += f"{to_small_caps('Anime:')} <code>{escape(query)}</code>\n"
    message += f"{to_small_caps('Found:')} {len(results)} {to_small_caps('characters')}\n\n"
    
    for i, char in enumerate(results, 1):
        name = escape(char.get('name', 'Unknown'))
        anime = escape(char.get('anime', 'Unknown'))
        rarity = parse_rarity(char.get('rarity'))
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        char_id = char.get('id', 'N/A')
        
        message += (
            f"{i}. <b>{name}</b>\n"
            f"   ✨ {rarity_display}\n"
            f"   🆔 ID: <code>{char_id}</code>\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='HTML')


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/id <character_id> - Get detailed info about a character by ID."""
    if not context.args:
        await update.message.reply_text(
            to_small_caps("Usage: /id <character_id>\n"
                         "Example: /id 123")
        )
        return
    
    try:
        char_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Character ID must be a number."))
        return
    
    # Get character from database
    try:
        character = await collection.find_one({'id': char_id})
    except Exception as e:
        LOGGER.error(f"Error fetching character: {e}")
        await update.message.reply_text(to_small_caps("❌ Error fetching character. Please try again."))
        return
    
    if not character:
        await update.message.reply_text(to_small_caps(f"❌ Character with ID {char_id} not found."))
        return
    
    # Format character info
    name = escape(character.get('name', 'Unknown'))
    anime = escape(character.get('anime', 'Unknown'))
    rarity = parse_rarity(character.get('rarity'))
    rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
    char_id = character.get('id', 'N/A')
    img_url = character.get('img_url', '')
    
    message = (
        f"<b>{to_small_caps('👤 Character Info')}</b>\n\n"
        f"<b>{name}</b>\n\n"
        f"🎬 <b>{to_small_caps('Anime:')}</b> {anime}\n"
        f"✨ <b>{to_small_caps('Rarity:')}</b> {rarity_display}\n"
        f"🆔 <b>{to_small_caps('ID:')}</b> <code>{char_id}</code>\n"
    )
    
    # Send with image if available
    if img_url:
        try:
            await update.message.reply_photo(
                photo=img_url,
                caption=message,
                parse_mode='HTML'
            )
        except Exception as e:
            LOGGER.error(f"Error sending character image: {e}")
            await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text(message, parse_mode='HTML')


# Register handlers
application.add_handler(CommandHandler("search", search_cmd, block=False))
application.add_handler(CommandHandler("anime", anime_cmd, block=False))
application.add_handler(CommandHandler("id", id_cmd, block=False))

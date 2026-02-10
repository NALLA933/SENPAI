"""
Upload Module
Handles uploading new characters to the database.
"""

import os
import aiohttp
from html import escape
from typing import Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, collection, LOGGER, OWNER_ID, SUDO_USERS
from shivu.config import Config
from shivu.utils import RARITY_MAP, to_small_caps, parse_rarity

# ImgBB API configuration
IMGBB_API_KEY = Config.IMGBB_API_KEY


async def upload_to_imgbb(image_data: bytes) -> Optional[str]:
    """Upload image to ImgBB and return URL."""
    if not IMGBB_API_KEY:
        LOGGER.error("ImgBB API key not configured")
        return None
    
    url = "https://api.imgbb.com/1/upload"
    
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('key', IMGBB_API_KEY)
            data.add_field('image', image_data)
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        return result['data']['url']
                    else:
                        LOGGER.error(f"ImgBB upload failed: {result}")
                else:
                    LOGGER.error(f"ImgBB API error: {response.status}")
    except Exception as e:
        LOGGER.error(f"Error uploading to ImgBB: {e}")
    
    return None


async def upload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/upload - Upload a new character (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    # Check for reply with image
    if not update.message.reply_to_message:
        await update.message.reply_text(
            to_small_caps("Usage: Reply to an image with /upload <name> <anime> <rarity>\n"
                         "Example: /upload Naruto Naruto 3")
        )
        return
    
    # Get image
    reply = update.message.reply_to_message
    photo = reply.photo[-1] if reply.photo else None
    
    if not photo:
        await update.message.reply_text(to_small_caps("❌ Please reply to an image."))
        return
    
    # Parse arguments
    if len(context.args) < 3:
        await update.message.reply_text(
            to_small_caps("Usage: Reply to an image with /upload <name> <anime> <rarity>\n"
                         "Example: /upload Naruto Naruto 3\n\n"
                         "Rarity levels:\n"
                         "1 = ⚪ Common\n"
                         "2 = 🔵 Rare\n"
                         "3 = 🟡 Legendary\n"
                         "4 = 💮 Special\n"
                         "5 = 👹 Ancient\n"
                         "... and more")
        )
        return
    
    name = context.args[0]
    anime = context.args[1]
    
    try:
        rarity = int(context.args[2])
        if rarity not in RARITY_MAP:
            raise ValueError
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Invalid rarity. Use 1-15."))
        return
    
    # Download image
    status_message = await update.message.reply_text(to_small_caps("🔄 Downloading image..."))
    
    try:
        file = await context.bot.get_file(photo.file_id)
        image_data = await file.download_as_bytearray()
    except Exception as e:
        LOGGER.error(f"Error downloading image: {e}")
        await status_message.edit_text(to_small_caps("❌ Error downloading image."))
        return
    
    # Upload to ImgBB
    await status_message.edit_text(to_small_caps("🔄 Uploading to ImgBB..."))
    
    img_url = await upload_to_imgbb(bytes(image_data))
    
    if not img_url:
        await status_message.edit_text(
            to_small_caps("❌ Failed to upload image.\n"
                         "Make sure IMGBB_API_KEY is configured in your .env file.")
        )
        return
    
    # Generate character ID
    try:
        last_char = await collection.find_one(sort=[("id", -1)])
        new_id = (last_char.get('id', 0) + 1) if last_char else 1
    except Exception as e:
        LOGGER.error(f"Error getting last character ID: {e}")
        new_id = 1
    
    # Insert character
    try:
        character = {
            'id': new_id,
            'name': name,
            'anime': anime,
            'rarity': rarity,
            'img_url': img_url
        }
        
        await collection.insert_one(character)
        
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        await status_message.edit_text(
            f"✅ <b>{to_small_caps('Character Uploaded')}</b>\n\n"
            f"👤 {escape(name)}\n"
            f"🎬 {escape(anime)}\n"
            f"✨ {rarity_display}\n"
            f"🆔 ID: <code>{new_id}</code>\n"
            f"🔗 <a href='{img_url}'>Image</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        LOGGER.info(f"Character uploaded: {name} (ID: {new_id}) by user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"Error inserting character: {e}")
        await status_message.edit_text(to_small_caps("❌ Error saving character to database."))


async def uploadurl_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/uploadurl <name> <anime> <rarity> <url> - Upload character with URL (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            to_small_caps("Usage: /uploadurl <name> <anime> <rarity> <url>\n"
                         "Example: /uploadurl Naruto Naruto 3 https://example.com/image.jpg")
        )
        return
    
    name = context.args[0]
    anime = context.args[1]
    
    try:
        rarity = int(context.args[2])
        if rarity not in RARITY_MAP:
            raise ValueError
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Invalid rarity. Use 1-15."))
        return
    
    img_url = context.args[3]
    
    # Validate URL
    if not img_url.startswith(('http://', 'https://')):
        await update.message.reply_text(to_small_caps("❌ Invalid URL. Must start with http:// or https://"))
        return
    
    # Generate character ID
    try:
        last_char = await collection.find_one(sort=[("id", -1)])
        new_id = (last_char.get('id', 0) + 1) if last_char else 1
    except Exception as e:
        LOGGER.error(f"Error getting last character ID: {e}")
        new_id = 1
    
    # Insert character
    try:
        character = {
            'id': new_id,
            'name': name,
            'anime': anime,
            'rarity': rarity,
            'img_url': img_url
        }
        
        await collection.insert_one(character)
        
        rarity_display = RARITY_MAP.get(rarity, '⚪ Common')
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Character Uploaded')}</b>\n\n"
            f"👤 {escape(name)}\n"
            f"🎬 {escape(anime)}\n"
            f"✨ {rarity_display}\n"
            f"🆔 ID: <code>{new_id}</code>\n"
            f"🔗 <a href='{img_url}'>Image</a>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        LOGGER.info(f"Character uploaded via URL: {name} (ID: {new_id}) by user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"Error inserting character: {e}")
        await update.message.reply_text(to_small_caps("❌ Error saving character to database."))


async def deletechar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/deletechar <id> - Delete a character from database (Admin only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners and sudo users."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /deletechar <character_id>"))
        return
    
    try:
        char_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(to_small_caps("❌ Character ID must be a number."))
        return
    
    # Find character
    try:
        character = await collection.find_one({'id': char_id})
    except Exception as e:
        LOGGER.error(f"Error finding character: {e}")
        await update.message.reply_text(to_small_caps("❌ Error finding character."))
        return
    
    if not character:
        await update.message.reply_text(to_small_caps(f"❌ Character with ID {char_id} not found."))
        return
    
    # Delete character
    try:
        await collection.delete_one({'id': char_id})
        
        name = escape(character.get('name', 'Unknown'))
        
        await update.message.reply_text(
            f"✅ <b>{to_small_caps('Character Deleted')}</b>\n\n"
            f"👤 {name}\n"
            f"🆔 ID: <code>{char_id}</code>",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Character deleted: {name} (ID: {char_id}) by user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"Error deleting character: {e}")
        await update.message.reply_text(to_small_caps("❌ Error deleting character."))


# Register handlers
application.add_handler(CommandHandler("upload", upload_cmd, block=False))
application.add_handler(CommandHandler("uploadurl", uploadurl_cmd, block=False))
application.add_handler(CommandHandler("deletechar", deletechar_cmd, block=False))

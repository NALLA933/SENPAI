import asyncio
import random
from html import escape
from typing import Optional, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

from shivu import (
    application, 
    user_collection, 
    pm_users, 
    LOGGER, 
    SUPPORT_CHAT, 
    UPDATE_CHAT, 
    BOT_USERNAME,
    VIDEO_URL
)
from shivu.utils import to_small_caps

_stats_cache: dict = {}
_stats_lock = asyncio.Lock()


async def _register_user(
    user_id: int, 
    first_name: str, 
    username: Optional[str]
) -> None:
    try:
        await pm_users.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'user_id': user_id,
                    'first_name': first_name,
                    'username': username,
                    'last_seen': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        await user_collection.update_one(
            {'id': user_id},
            {
                '$setOnInsert': {
                    'id': user_id,
                    'first_name': first_name,
                    'username': username,
                    'characters': [],
                    'balance': 0,
                    'favorites': [],
                    'joined': datetime.utcnow()
                }
            },
            upsert=True
        )
    except Exception as e:
        LOGGER.error(f"User registration failed for {user_id}: {e}", exc_info=True)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    
    user = update.effective_user
    user_id = user.id
    first_name = escape(user.first_name)
    
    username = getattr(user, 'username', None)
    asyncio.create_task(_register_user(user_id, user.first_name, username))
    
    selected_video = None
    if VIDEO_URL and len(VIDEO_URL) > 0:
        selected_video = random.choice(VIDEO_URL)
    
    tagline = "Guess characters that spawn in your groups and build your ultimate harem!"
    
    welcome_text = (
        f"<b>👋 {to_small_caps('Welcome')}, {first_name}!</b>\n\n"
        f"{to_small_caps(tagline)}\n\n"
        f"<i>{to_small_caps('Click the button below to see all commands')}</i>"
    )
    
    keyboard_buttons: List[List[InlineKeyboardButton]] = []
    
    keyboard_buttons.append([
        InlineKeyboardButton("📖 ʜᴇʟᴘ", callback_data="help_menu")
    ])
    
    if BOT_USERNAME:
        keyboard_buttons.append([
            InlineKeyboardButton(
                to_small_caps("➕ Add to Group"),
                url=f"https://t.me/{BOT_USERNAME.lstrip('@')}?startgroup=true"
            )
        ])
    
    if SUPPORT_CHAT:
        keyboard_buttons.append([
            InlineKeyboardButton(
                to_small_caps("💬 Support"),
                url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
            ),
            InlineKeyboardButton(
                to_small_caps("📢 Updates"),
                url=f"https://t.me/{UPDATE_CHAT.lstrip('@')}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
    
    try:
        if selected_video:
            if selected_video.startswith(('http://', 'https://')):
                await update.message.reply_video(
                    video=selected_video,
                    caption=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                    supports_streaming=True
                )
            else:
                await update.message.reply_video(
                    video=selected_video,
                    caption=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        else:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
    except Exception as e:
        LOGGER.error(f"Start video failed: {e}")
        try:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()
    
    if query.data == "help_menu":
        help_text = (
            "✦ ɢᴜɪᴅᴀɴᴄᴇ ғʀᴏᴍ sᴇɴᴘᴀɪ ✦\n\n"
            "✦ ── 『 ʜᴀʀᴇᴍ ᴄᴏᴍᴍᴀɴᴅ ʟɪsᴛ 』 ── ✦\n\n"
            "/guess  \n"
            "↳ ɢᴜᴇss ᴛʜᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ  \n\n"
            "/bal  \n"
            "↳ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ʙᴀʟᴀɴᴄᴇ  \n\n"
            "/fav  \n"
            "↳ ᴀᴅᴅ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴛᴏ ғᴀᴠᴏʀɪᴛᴇs  \n\n"
            "/collection  \n"
            "↳ ᴠɪᴇᴡ ʏᴏᴜʀ ʜᴀʀᴇᴍ ᴄᴏʟʟᴇᴄᴛɪᴏɴ  \n\n"
            "/leaderboard  \n"
            "↳ ᴄʜᴇᴄᴋ ᴛʜᴇ ᴛᴏᴘ ᴜsᴇʀ ʟɪsᴛ  \n\n"
            "/gift  \n"
            "↳ ɢɪғᴛ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴜsᴇʀ  \n\n"
            "/trade  \n"
            "↳ ᴛʀᴀᴅᴇ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴡɪᴛʜ ᴀɴᴏᴛʜᴇʀ ᴜsᴇʀ  \n\n"
            "/shop  \n"
            "↳ ᴏᴘᴇɴ ᴛʜᴇ sʜᴏᴘ  \n\n"
            "/smode  \n"
            "↳ ᴄʜᴀɴɢᴇ ʜᴀʀᴇᴍ ᴍᴏᴅᴇ  \n\n"
            "/s  \n"
            "↳ ᴠɪᴇᴡ ᴄʜᴀʀᴀᴄᴛᴇʀ ғʀᴏᴍ ᴡᴀɪғᴜ ɪᴅ  \n\n"
            "/find  \n"
            "↳ ғɪɴᴅ ʜᴏᴡ ᴍᴀɴʏ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴇxɪsᴛ ᴡɪᴛʜ ᴀ ɴᴀᴍᴇ  \n\n"
            "/redeem  \n"
            "↳ ʀᴇᴅᴇᴇᴍ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴀɴᴅ ᴄᴏɪɴs  \n\n"
            "/sclaim  \n"
            "↳ ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ᴡᴀɪғᴜ  \n\n"
            "/claim  \n"
            "↳ ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ᴄᴏᴜɴᴛ  \n\n"
            "/pay  \n"
            "↳ sᴇɴᴅ ᴄᴏɪɴs ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴜsᴇʀ  \n\n"
            "✦ ───────────────── ✦"
        )
        
        keyboard = [[
            InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="start_back")
        ]]
        
        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
            
    elif query.data == "start_back":
        await start_callback_handler(update, context)


async def start_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    user = update.effective_user
    if not user:
        return
    
    first_name = escape(user.first_name)
    tagline = "Guess characters that spawn in your groups and build your ultimate harem!"
    
    welcome_text = (
        f"<b>👋 {to_small_caps('Welcome')}, {first_name}!</b>\n\n"
        f"{to_small_caps(tagline)}\n\n"
        f"<i>{to_small_caps('Click the button below to see all commands')}</i>"
    )
    
    keyboard_buttons: List[List[InlineKeyboardButton]] = []
    
    keyboard_buttons.append([
        InlineKeyboardButton("📖 ʜᴇʟᴘ", callback_data="help_menu")
    ])
    
    if BOT_USERNAME:
        keyboard_buttons.append([
            InlineKeyboardButton(
                to_small_caps("➕ Add to Group"),
                url=f"https://t.me/{BOT_USERNAME.lstrip('@')}?startgroup=true"
            )
        ])
    
    if SUPPORT_CHAT:
        keyboard_buttons.append([
            InlineKeyboardButton(
                to_small_caps("💬 Support"),
                url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
            ),
            InlineKeyboardButton(
                to_small_caps("📢 Updates"),
                url=f"https://t.me/{UPDATE_CHAT.lstrip('@')}"
            )
        ])
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard_buttons),
        parse_mode=ParseMode.HTML
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    
    try:
        from shivu import collection, top_global_groups_collection
        
        users = await user_collection.count_documents({})
        chars = await collection.count_documents({})
        groups = await top_global_groups_collection.count_documents({})
        
        stats_text = (
            f"<b>{to_small_caps('📊 Bot Statistics')}</b>\n\n"
            f"👥 <b>{to_small_caps('Users:')}</b> <code>{users:,}</code>\n"
            f"💬 <b>{to_small_caps('Groups:')}</b> <code>{groups:,}</code>\n"
            f"🎭 <b>{to_small_caps('Characters:')}</b> <code>{chars:,}</code>"
        )
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        LOGGER.error(f"Stats error: {e}")
        await update.message.reply_text(
            to_small_caps("❌ Error fetching statistics."),
            parse_mode=ParseMode.HTML
        )


application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("stats", stats_cmd))

application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="^help_menu$"))
application.add_handler(CallbackQueryHandler(start_callback_handler, pattern="^start_back$"))

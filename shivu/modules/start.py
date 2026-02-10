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

# Cache for stats
_stats_cache: dict = {}
_stats_lock = asyncio.Lock()


async def _register_user(
    user_id: int, 
    first_name: str, 
    username: Optional[str]
) -> None:
    """Fire-and-forget user registration."""
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
    """/start - Handle bot initialization with video support."""
    if not update.effective_user or not update.message:
        return
    
    user = update.effective_user
    user_id = user.id
    first_name = escape(user.first_name)
    
    # Register user
    username = getattr(user, 'username', None)
    asyncio.create_task(_register_user(user_id, user.first_name, username))
    
    # Pick random video from VIDEO_URL list
    selected_video = None
    if VIDEO_URL and len(VIDEO_URL) > 0:
        selected_video = random.choice(VIDEO_URL)
    
    # Build welcome message (simplified without Quick Start and Commands)
    tagline = "ɪ ᴀᴍ ᴀɴ ᴀᴅᴠᴀɴᴄᴇᴅ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ʙᴏᴛ. ɢᴜᴇꜱꜱ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ᴛʜᴀᴛ ꜱᴘᴀᴡɴ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘꜱ ᴀɴᴅ ʙᴜɪʟᴅ ʏᴏᴜʀ ᴜʟᴛɪᴍᴀᴛᴇ ʜᴀʀᴇᴍ!"
    
    welcome_text = (
        f"<b>👋 {to_small_caps('Welcome')}, {first_name}!</b>\n\n"
        f"{to_small_caps(tagline)}\n\n"
    )
    
    # Build keyboard
    keyboard_buttons: List[List[InlineKeyboardButton]] = []
    
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
    
    # VIDEO HANDLING
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


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help - Show detailed command help."""
    if not update.message:
        return
    
    help_text = (
        f"<b>{to_small_caps('📖 Command Help')}</b>\n\n"
        f"<b>{to_small_caps('🎮 Collection:')}</b>\n"
        f"• <code>/guess</code> &lt;name&gt; — {to_small_caps('Claim character')}\n"
        f"• <code>/harem</code> — {to_small_caps('View collection')}\n"
        f"• <code>/fav</code> &lt;id&gt; — {to_small_caps('Set favorite')}\n"
        f"• <code>/gift</code> &lt;id&gt; &lt;user&gt; — {to_small_caps('Gift character')}\n\n"
        f"<b>{to_small_caps('💰 Economy:')}</b>\n"
        f"• <code>/balance</code> — {to_small_caps('Check coins')}\n"
        f"• <code>/pay</code> &lt;user&gt; &lt;amt&gt; — {to_small_caps('Transfer')}\n"
        f"• <code>/shop</code> — {to_small_caps('Buy characters')}\n\n"
        f"<b>{to_small_caps('📊 Stats:')}</b>\n"
        f"• <code>/leaderboard</code>, <code>/top</code>, <code>/stats</code>"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stats - Show bot statistics."""
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


# Register handlers
application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("help", help_cmd))
application.add_handler(CommandHandler("stats", stats_cmd))

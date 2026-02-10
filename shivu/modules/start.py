"""
Start Module
Handles start command, user registration, and basic bot info.
Optimized for python-telegram-bot v22.6
"""

import asyncio
from html import escape
from typing import Optional, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler, filters
from telegram.constants import ParseMode

from shivu import (
    application, 
    user_collection, 
    pm_users, 
    LOGGER, 
    SUPPORT_CHAT, 
    UPDATE_CHAT, 
    BOT_USERNAME
)
from shivu.utils import to_small_caps

# Cache for stats command (TTL: 5 minutes)
_stats_cache: dict = {}
_stats_lock = asyncio.Lock()


async def _register_user(
    user_id: int, 
    first_name: str, 
    username: Optional[str]
) -> None:
    """Fire-and-forget user registration."""
    try:
        # Update PM users collection
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
        
        # Ensure user in main collection
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
    """/start - Handle bot initialization with deep linking support."""
    if not update.effective_user or not update.message:
        return
    
    user = update.effective_user
    user_id = user.id
    first_name = escape(user.first_name)
    
    # Handle deep linking (referrals or specific actions)
    args = context.args
    if args and len(args) > 0:
        payload = args[0]
        # Handle specific start parameters (e.g., ref codes, character shares)
        if payload.startswith("ref_"):
            # Handle referral logic here
            pass
        elif payload.startswith("char_"):
            # Handle shared character logic here  
            pass
    
    # Register user asynchronously (non-blocking)
    username = getattr(user, 'username', None)
    asyncio.create_task(_register_user(user_id, user.first_name, username))
    
    # Build welcome message with proper formatting
    tagline = "I am an advanced character collection bot. Guess characters that spawn in your groups and build your ultimate harem!"
    
    welcome_text = (
        f"<b>👋 {to_small_caps('Welcome')}, {first_name}!</b>\n\n"
        f"{to_small_caps(tagline)}\n\n"
        f"<b>{to_small_caps('🎮 Quick Start:')}</b>\n"
        f"• Add me to a group\n"
        f"• Wait for characters to spawn\n"  
        f"• Use /guess to claim them!\n\n"
        f"<b>{to_small_caps('📚 Essential Commands:')}</b>\n"
        f"• /guess &lt;name&gt; — {to_small_caps('Guess character name')}\n"
        f"• /harem — {to_small_caps('View your collection')}\n"
        f"• /balance — {to_small_caps('Check coin balance')}\n"
        f"• /shop — {to_small_caps('Buy characters')}\n"
        f"• /help — {to_small_caps('Full command list')}"
    )
    
    # Build dynamic keyboard
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
                to_small_caps("💬 Support Group"),
                url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
            )
        ])
        
    if UPDATE_CHAT:
        keyboard_buttons.append([
            InlineKeyboardButton(
                to_small_caps("📢 Updates Channel"),
                url=f"https://t.me/{UPDATE_CHAT.lstrip('@')}"
            )
        ])
    
    # Add inline help button
    keyboard_buttons.append([
        InlineKeyboardButton(
            to_small_caps("📖 Help"),
            callback_data="help_menu"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    # Send with retry logic for network errors
    try:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        LOGGER.error(f"Failed to send start message: {e}")
        # Fallback without markup
        try:
            await update.message.reply_text(
                f"Welcome {first_name}! Use /help to see commands.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help - Show detailed command help with categories."""
    if not update.message:
        return
    
    # Create paginated or categorized help
    help_text = (
        f"<b>{to_small_caps('📖 Command Help')}</b>\n\n"
        f"<b>{to_small_caps('🎮 Collection:')}</b>\n"
        f"• <code>/guess</code> &lt;name&gt; — {to_small_caps('Attempt to claim spawned character')}\n"
        f"• <code>/harem</code> [page] — {to_small_caps('Browse your collection')}\n"
        f"• <code>/fav</code> &lt;id&gt; — {to_small_caps('Mark character as favorite')}\n"
        f"• <code>/gift</code> &lt;id&gt; &lt;user&gt; — {to_small_caps('Gift a character')}\n\n"
        f"<b>{to_small_caps('💰 Economy:')}</b>\n"
        f"• <code>/balance</code> — {to_small_caps('Check your coins')}\n"
        f"• <code>/pay</code> &lt;user&gt; &lt;amount&gt; — {to_small_caps('Transfer coins')}\n"
        f"• <code>/shop</code> — {to_small_caps('Browse character shop')}\n"
        f"• <code>/buy</code> &lt;item&gt; — {to_small_caps('Purchase item')}\n"
        f"• <code>/redeem</code> &lt;code&gt; — {to_small_caps('Redeem gift code')}\n\n"
        f"<b>{to_small_caps('🔍 Search:')}</b>\n"
        f"• <code>/search</code> &lt;name&gt; — {to_small_caps('Find characters by name')}\n"
        f"• <code>/anime</code> &lt;name&gt; — {to_small_caps('Find by anime series')}\n"
        f"• <code>/id</code> &lt;id&gt; — {to_small_caps('Character details by ID')}\n\n"
        f"<b>{to_small_caps('📊 Stats:')}</b>\n"
        f"• <code>/leaderboard</code> — {to_small_caps('Global rankings')}\n"
        f"• <code>/top</code> — {to_small_caps('Top 10 collectors')}\n"
        f"• <code>/grouptop</code> — {to_small_caps('Top active groups')}\n"
        f"• <code>/stats</code> — {to_small_caps('Bot statistics')}\n\n"
        f"<b>{to_small_caps('⚙️ Settings:')}</b>\n"
        f"• <code>/smode</code> — {to_small_caps('Change harem filter mode')}\n\n"
        f"<i>{to_small_caps('Tip: Use these commands in groups to interact with spawned characters!')}</i>"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stats - Show bot statistics with caching."""
    if not update.message:
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    
    # Check cache first (avoid DB spam)
    cache_key = "global_stats"
    current_time = asyncio.get_event_loop().time()
    
    async with _stats_lock:
        if cache_key in _stats_cache:
            cached_data, timestamp = _stats_cache[cache_key]
            if current_time - timestamp < 300:  # 5 min cache
                await update.message.reply_text(
                    cached_data, 
                    parse_mode=ParseMode.HTML
                )
                return
    
    try:
        # Run aggregations in parallel
        from shivu import collection, top_global_groups_collection
        
        tasks = [
            collection.count_documents({}),
            user_collection.count_documents({}),
            top_global_groups_collection.count_documents({}),
            _get_total_collected()
        ]
        
        chars, users, groups, collected = await asyncio.gather(*tasks)
        
        stats_text = (
            f"<b>{to_small_caps('📊 Bot Statistics')}</b>\n\n"
            f"👥 <b>{to_small_caps('Users:')}</b> <code>{users:,}</code>\n"
            f"💬 <b>{to_small_caps('Groups:')}</b> <code>{groups:,}</code>\n"
            f"🎭 <b>{to_small_caps('Characters:')}</b> <code>{chars:,}</code>\n"
            f"📦 <b>{to_small_caps('Collected:')}</b> <code>{collected:,}</code>\n\n"
            f"<i>{to_small_caps('Requested by:')} {update.effective_user.first_name}</i>"
        )
        
        # Update cache
        async with _stats_lock:
            _stats_cache[cache_key] = (stats_text, current_time)
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        LOGGER.error(f"Stats error: {e}", exc_info=True)
        await update.message.reply_text(
            to_small_caps("❌ Failed to fetch statistics. Please try again later."),
            parse_mode=ParseMode.HTML
        )


async def _get_total_collected() -> int:
    """Helper to count total collected characters."""
    try:
        pipeline = [
            {"$match": {"characters": {"$exists": True, "$ne": []}}},
            {"$group": {
                "_id": None, 
                "total": {"$sum": {"$size": "$characters"}}
            }}
        ]
        result = await user_collection.aggregate(pipeline).to_list(1)
        return result[0]["total"] if result else 0
    except Exception:
        return 0


async def start_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from start menu."""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()
    
    if query.data == "help_menu":
        # Show help in callback
        help_text = (
            f"<b>{to_small_caps('Quick Help')}</b>\n\n"
            f"1. Add bot to group\n"
            f"2. Characters spawn randomly\n"
            f"3. First to guess gets it!\n\n"
            f"{to_small_caps('Use /help for full details')}"
        )
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    to_small_caps("🔙 Back"),
                    callback_data="start_back"
                )
            ]])
        )
    elif query.data == "start_back":
        # Re-show start menu
        await start_cmd(update, context)


# Register handlers (PTB 22.x syntax - block parameter removed)
application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("help", help_cmd))
application.add_handler(CommandHandler("stats", stats_cmd))

# Callback handler for start menu buttons
application.add_handler(CallbackQueryHandler(start_callback_handler, pattern="^(help_menu|start_back)$"))

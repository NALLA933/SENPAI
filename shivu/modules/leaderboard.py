"""
Leaderboard Module
Handles daily, weekly, and all-time leaderboards for users and groups.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import (
    application,
    user_collection,
    group_user_totals_collection,
    top_global_groups_collection,
    LOGGER,
)
from shivu.utils import to_small_caps

# Daily tracking collections
daily_user_guess = {}
daily_group_guess = {}

# Weekly tracking
weekly_user_guess: Dict[int, Dict] = {}
weekly_group_guess: Dict[int, Dict] = {}

# Cache for performance
user_cache: Dict[int, Dict] = {}
CACHE_TTL = 300


async def update_daily_user_guess(user_id: int, username: str, first_name: str):
    """Update daily guess count for a user."""
    if user_id not in daily_user_guess:
        daily_user_guess[user_id] = {
            'username': username,
            'first_name': first_name,
            'count': 0
        }
    daily_user_guess[user_id]['count'] += 1
    
    # Also update weekly
    if user_id not in weekly_user_guess:
        weekly_user_guess[user_id] = {
            'username': username,
            'first_name': first_name,
            'count': 0
        }
    weekly_user_guess[user_id]['count'] += 1


async def update_daily_group_guess(group_id: int, group_name: str):
    """Update daily guess count for a group."""
    if group_id not in daily_group_guess:
        daily_group_guess[group_id] = {
            'group_name': group_name,
            'count': 0
        }
    daily_group_guess[group_id]['count'] += 1
    
    # Also update weekly
    if group_id not in weekly_group_guess:
        weekly_group_guess[group_id] = {
            'group_name': group_name,
            'count': 0
        }
    weekly_group_guess[group_id]['count'] += 1


def reset_daily_leaderboards():
    """Reset daily leaderboards (should be called once per day)."""
    global daily_user_guess, daily_group_guess
    daily_user_guess = {}
    daily_group_guess = {}
    LOGGER.info("Daily leaderboards reset")


def reset_weekly_leaderboards():
    """Reset weekly leaderboards (should be called once per week)."""
    global weekly_user_guess, weekly_group_guess
    weekly_user_guess = {}
    weekly_group_guess = {}
    LOGGER.info("Weekly leaderboards reset")


async def get_user_info_cached(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict]:
    """Get user info with caching."""
    if user_id in user_cache:
        cached = user_cache[user_id]
        if (datetime.now() - cached.get('timestamp', datetime.min)).seconds < CACHE_TTL:
            return cached
    
    try:
        user = await context.bot.get_chat(user_id)
        user_cache[user_id] = {
            'id': user_id,
            'first_name': user.first_name,
            'username': getattr(user, 'username', None),
            'timestamp': datetime.now()
        }
        return user_cache[user_id]
    except Exception as e:
        LOGGER.error(f"Error getting user info for {user_id}: {e}")
        return None


async def get_user_name(user_id: int, context: ContextTypes.DEFAULT_TYPE, fallback: str = "Unknown") -> str:
    """Get user display name."""
    user_info = await get_user_info_cached(user_id, context)
    if user_info:
        return escape(user_info['first_name'])
    return fallback


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/leaderboard - Show global user leaderboard."""
    await _show_leaderboard(update, context, 'global_users', 0)


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaderboard navigation callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("lb:"):
        return
    
    parts = data.split(":")
    if len(parts) != 3:
        return
    
    _, lb_type, page_str = parts
    page = int(page_str)
    
    await _show_leaderboard(update, context, lb_type, page)


async def _show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, lb_type: str, page: int):
    """Show leaderboard based on type and page."""
    page_size = 10
    
    if lb_type == 'global_users':
        title = "🏆 Global User Leaderboard"
        
        # Get top users by character count
        pipeline = [
            {"$match": {"characters": {"$exists": True, "$ne": []}}},
            {"$project": {
                "id": 1,
                "first_name": 1,
                "username": 1,
                "character_count": {"$size": {"$ifNull": ["$characters", []]}}
            }},
            {"$sort": {"character_count": -1}},
            {"$skip": page * page_size},
            {"$limit": page_size}
        ]
        
        cursor = user_collection.aggregate(pipeline)
        entries = await cursor.to_list(length=page_size)
        
        if not entries:
            if page == 0:
                text = to_small_caps("No users have collected characters yet!")
            else:
                text = to_small_caps("No more entries.")
            await _send_or_edit(update, text)
            return
        
        message = f"<b>{to_small_caps(title)}</b>\n\n"
        
        for i, entry in enumerate(entries, start=page * page_size + 1):
            name = escape(entry.get('first_name', 'Unknown'))
            count = entry.get('character_count', 0)
            message += f"{i}. {name} - {count} characters\n"
    
    elif lb_type == 'daily_users':
        title = "📅 Daily User Leaderboard"
        
        sorted_users = sorted(
            daily_user_guess.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[page * page_size:(page + 1) * page_size]
        
        if not sorted_users:
            if page == 0:
                text = to_small_caps("No guesses today yet!")
            else:
                text = to_small_caps("No more entries.")
            await _send_or_edit(update, text)
            return
        
        message = f"<b>{to_small_caps(title)}</b>\n\n"
        
        for i, (user_id, data) in enumerate(sorted_users, start=page * page_size + 1):
            name = escape(data.get('first_name', 'Unknown'))
            count = data.get('count', 0)
            message += f"{i}. {name} - {count} guesses\n"
    
    elif lb_type == 'daily_groups':
        title = "📅 Daily Group Leaderboard"
        
        sorted_groups = sorted(
            daily_group_guess.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[page * page_size:(page + 1) * page_size]
        
        if not sorted_groups:
            if page == 0:
                text = to_small_caps("No group activity today yet!")
            else:
                text = to_small_caps("No more entries.")
            await _send_or_edit(update, text)
            return
        
        message = f"<b>{to_small_caps(title)}</b>\n\n"
        
        for i, (group_id, data) in enumerate(sorted_groups, start=page * page_size + 1):
            name = escape(data.get('group_name', 'Unknown Group'))
            count = data.get('count', 0)
            message += f"{i}. {name} - {count} guesses\n"
    
    elif lb_type == 'global_groups':
        title = "🏆 Global Group Leaderboard"
        
        pipeline = [
            {"$sort": {"count": -1}},
            {"$skip": page * page_size},
            {"$limit": page_size}
        ]
        
        cursor = top_global_groups_collection.aggregate(pipeline)
        entries = await cursor.to_list(length=page_size)
        
        if not entries:
            if page == 0:
                text = to_small_caps("No group activity recorded yet!")
            else:
                text = to_small_caps("No more entries.")
            await _send_or_edit(update, text)
            return
        
        message = f"<b>{to_small_caps(title)}</b>\n\n"
        
        for i, entry in enumerate(entries, start=page * page_size + 1):
            name = escape(entry.get('group_name', 'Unknown Group'))
            count = entry.get('count', 0)
            message += f"{i}. {name} - {count} guesses\n"
    
    else:
        message = to_small_caps("Unknown leaderboard type.")
    
    # Navigation buttons
    keyboard = []
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"lb:{lb_type}:{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"Page {page+1}", callback_data="noop"))
    
    # Check if there's a next page (simplified - assumes there might be)
    nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"lb:{lb_type}:{page+1}"))
    
    keyboard.append(nav_buttons)
    
    # Type switcher
    type_buttons = [
        InlineKeyboardButton("Global Users", callback_data="lb:global_users:0"),
        InlineKeyboardButton("Daily Users", callback_data="lb:daily_users:0"),
    ]
    keyboard.append(type_buttons)
    
    type_buttons2 = [
        InlineKeyboardButton("Daily Groups", callback_data="lb:daily_groups:0"),
        InlineKeyboardButton("Global Groups", callback_data="lb:global_groups:0"),
    ]
    keyboard.append(type_buttons2)
    
    markup = InlineKeyboardMarkup(keyboard)
    await _send_or_edit(update, message, markup)


async def _send_or_edit(update: Update, text: str, markup=None):
    """Send new message or edit existing one."""
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='HTML')
        except Exception:
            pass
    else:
        if update.message:
            await update.message.reply_text(text, reply_markup=markup, parse_mode='HTML')


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/top - Show top 10 global users."""
    pipeline = [
        {"$match": {"characters": {"$exists": True, "$ne": []}}},
        {"$project": {
            "id": 1,
            "first_name": 1,
            "username": 1,
            "character_count": {"$size": {"$ifNull": ["$characters", []]}}
        }},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ]
    
    cursor = user_collection.aggregate(pipeline)
    entries = await cursor.to_list(length=10)
    
    if not entries:
        await update.message.reply_text(to_small_caps("No users have collected characters yet!"))
        return
    
    message = f"<b>{to_small_caps('🏆 Top 10 Global Users')}</b>\n\n"
    
    for i, entry in enumerate(entries, start=1):
        name = escape(entry.get('first_name', 'Unknown'))
        count = entry.get('character_count', 0)
        
        # Medal for top 3
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        message += f"{medal}{i}. {name} - {count} characters\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def grouptop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/grouptop - Show top groups."""
    pipeline = [
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    cursor = top_global_groups_collection.aggregate(pipeline)
    entries = await cursor.to_list(length=10)
    
    if not entries:
        await update.message.reply_text(to_small_caps("No group activity recorded yet!"))
        return
    
    message = f"<b>{to_small_caps('🏆 Top 10 Groups')}</b>\n\n"
    
    for i, entry in enumerate(entries, start=1):
        name = escape(entry.get('group_name', 'Unknown Group'))
        count = entry.get('count', 0)
        
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        message += f"{medal}{i}. {name} - {count} guesses\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


# Register handlers
application.add_handler(CommandHandler("leaderboard", leaderboard_cmd, block=False))
application.add_handler(CommandHandler("lb", leaderboard_cmd, block=False))
application.add_handler(CommandHandler("top", top_cmd, block=False))
application.add_handler(CommandHandler("grouptop", grouptop_cmd, block=False))
application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^lb:", block=False))

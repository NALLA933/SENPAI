"""
Start Module
Handles start command and user registration.
"""

from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, user_collection, pm_users, LOGGER, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, VIDEO_URL
from shivu.utils import to_small_caps


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start - Start the bot and show welcome message."""
    user_id = update.effective_user.id
    first_name = escape(update.effective_user.first_name)

    # Register user in PM users if in private chat
    if update.effective_chat.type == 'private':
        try:
            await pm_users.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'user_id': user_id,
                        'first_name': update.effective_user.first_name,
                        'username': getattr(update.effective_user, 'username', None)
                    }
                },
                upsert=True
            )
        except Exception as e:
            LOGGER.error(f"Error registering PM user: {e}")

    # Ensure user exists in user_collection
    try:
        await user_collection.update_one(
            {'id': user_id},
            {
                '$setOnInsert': {
                    'id': user_id,
                    'first_name': update.effective_user.first_name,
                    'username': getattr(update.effective_user, 'username', None),
                    'characters': [],
                    'balance': 0,
                    'favorites': []
                }
            },
            upsert=True
        )
    except Exception as e:
        LOGGER.error(f"Error ensuring user in collection: {e}")

    # Build welcome message
    message = (
        f"<b>👋 {to_small_caps('Welcome')}, {first_name}!</b>\n\n"
        f"{to_small_caps('I am a character collection bot. Guess characters that appear in your group chats and add them to your harem!')}\n\n"
        f"<b>{to_small_caps('📚 Commands:')}</b>\n"
        f"• /guess - {to_small_caps('Guess the character name')}\n"
        f"• /harem - {to_small_caps('View your collection')}\n"
        f"• /balance - {to_small_caps('Check your coin balance')}\n"
        f"• /shop - {to_small_caps('Buy characters with coins')}\n"
        f"• /leaderboard - {to_small_caps('View top collectors')}\n"
        f"• /search - {to_small_caps('Search for characters')}\n\n"
        f"{to_small_caps('Add me to your group and start collecting!')}"
    )

    # Build keyboard
    keyboard = []

    if SUPPORT_CHAT:
        keyboard.append([InlineKeyboardButton(
            to_small_caps("💬 Support Group"),
            url=f"https://t.me/{SUPPORT_CHAT}"
        )])

    if UPDATE_CHAT:
        keyboard.append([InlineKeyboardButton(
            to_small_caps("📢 Updates Channel"),
            url=f"https://t.me/{UPDATE_CHAT}"
        )])

    if BOT_USERNAME:
        keyboard.append([InlineKeyboardButton(
            to_small_caps("➕ Add to Group"),
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
        )])

    markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    # Send welcome message (Video + Caption or Text only)
    if update.message:
        try:
            if VIDEO_URL:
                # Send video with caption
                await update.message.reply_video(
                    video=VIDEO_URL,
                    caption=message,
                    reply_markup=markup,
                    parse_mode='HTML'
                )
            else:
                # Send text only if no video URL configured
                await update.message.reply_text(
                    message, 
                    reply_markup=markup, 
                    parse_mode='HTML'
                )
        except Exception as e:
            LOGGER.error(f"Error sending start message: {e}")
            # Fallback to text message if video fails
            await update.message.reply_text(
                message, 
                reply_markup=markup, 
                parse_mode='HTML'
            )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats - Show bot statistics."""
    from shivu import collection, user_collection, top_global_groups_collection

    try:
        # Get counts
        total_characters = await collection.count_documents({})
        total_users = await user_collection.count_documents({})
        total_groups = await top_global_groups_collection.count_documents({})

        # Get total collected characters
        pipeline = [
            {"$match": {"characters": {"$exists": True}}},
            {"$project": {"count": {"$size": {"$ifNull": ["$characters", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}}
        ]

        result = await user_collection.aggregate(pipeline).to_list(1)
        total_collected = result[0]['total'] if result else 0

        message = (
            f"<b>{to_small_caps('📊 Bot Statistics')}</b>\n\n"
            f"👥 {to_small_caps('Total Users:')} {total_users:,}\n"
            f"👥 {to_small_caps('Total Groups:')} {total_groups:,}\n"
            f"🎭 {to_small_caps('Total Characters:')} {total_characters:,}\n"
            f"📦 {to_small_caps('Total Collected:')} {total_collected:,}\n"
        )

        await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        LOGGER.error(f"Error getting stats: {e}")
        await update.message.reply_text(to_small_caps("❌ Error fetching statistics."))


# Register handlers
application.add_handler(CommandHandler("start", start_cmd, block=False))
application.add_handler(CommandHandler("stats", stats_cmd, block=False))

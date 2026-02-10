"""
Ping Module
Simple ping command to check bot responsiveness.
"""

import time
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, LOGGER
from shivu.utils import to_small_caps


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ping - Check bot response time."""
    start_time = time.time()
    
    # Send initial message
    message = await update.message.reply_text(to_small_caps("🏓 Pinging..."))
    
    # Calculate response time
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to ms
    
    # Get current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Edit message with results
    await message.edit_text(
        f"<b>{to_small_caps('🏓 Pong!')}</b>\n\n"
        f"⏱️ {to_small_caps('Response Time:')} <code>{response_time:.2f}ms</code>\n"
        f"🕐 {to_small_caps('Server Time:')} <code>{current_time}</code>\n\n"
        f"✅ {to_small_caps('Bot is running smoothly!')}",
        parse_mode='HTML'
    )
    
    LOGGER.info(f"Ping from user {update.effective_user.id}: {response_time:.2f}ms")


async def alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/alive - Check if bot is alive."""
    from shivu import collection, user_collection
    
    try:
        # Check database connection
        await collection.find_one()
        db_status = "✅ Connected"
    except Exception as e:
        db_status = f"❌ Error: {str(e)[:50]}"
        LOGGER.error(f"Database check failed: {e}")
    
    # Get uptime (approximate since bot start)
    uptime = "Running"
    
    await update.message.reply_text(
        f"<b>{to_small_caps('🤖 Bot Status')}</b>\n\n"
        f"✅ {to_small_caps('Status:')} Alive\n"
        f"🗄️ {to_small_caps('Database:')} {db_status}\n"
        f"⏱️ {to_small_caps('Uptime:')} {uptime}\n\n"
        f"{to_small_caps('Bot is operational!')}",
        parse_mode='HTML'
    )


# Register handlers
application.add_handler(CommandHandler("ping", ping_cmd, block=False))
application.add_handler(CommandHandler("alive", alive_cmd, block=False))

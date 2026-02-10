"""
Backup Module
Handles database backup and restore operations.
"""

import json
import os
from datetime import datetime
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from shivu import application, db, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import to_small_caps

# Backup configuration
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)


async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/backup - Create a database backup (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    status_message = await update.message.reply_text(to_small_caps("🔄 Creating backup..."))
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
        
        backup_data = {
            "timestamp": timestamp,
            "database": "Character_catcher",
            "collections": {}
        }
        
        # Get all collections
        collections = await db.list_collection_names()
        
        for coll_name in collections:
            collection = db[coll_name]
            documents = []
            
            async for doc in collection.find():
                # Convert ObjectId to string
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                documents.append(doc)
            
            backup_data["collections"][coll_name] = {
                "count": len(documents),
                "documents": documents
            }
        
        # Save to file
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Calculate total
        total_docs = sum(c["count"] for c in backup_data["collections"].values())
        file_size = os.path.getsize(backup_file) / 1024  # KB
        
        await status_message.edit_text(
            f"✅ <b>{to_small_caps('Backup Created')}</b>\n\n"
            f"📁 {to_small_caps('File:')} <code>{os.path.basename(backup_file)}</code>\n"
            f"📊 {to_small_caps('Collections:')} {len(collections)}\n"
            f"📦 {to_small_caps('Documents:')} {total_docs:,}\n"
            f"💾 {to_small_caps('Size:')} {file_size:.2f} KB\n"
            f"🕐 {to_small_caps('Time:')} {timestamp}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Backup created: {backup_file} ({total_docs} documents)")
        
    except Exception as e:
        LOGGER.error(f"Error creating backup: {e}")
        await status_message.edit_text(to_small_caps(f"❌ Error creating backup: {str(e)[:100]}"))


async def listbackups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/listbackups - List all backups (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    try:
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')],
            reverse=True
        )
        
        if not backups:
            await update.message.reply_text(to_small_caps("❌ No backups found."))
            return
        
        message = f"<b>{to_small_caps('📁 Available Backups')}</b>\n\n"
        
        for i, backup in enumerate(backups[:20], 1):  # Show last 20
            file_path = os.path.join(BACKUP_DIR, backup)
            file_size = os.path.getsize(file_path) / 1024
            message += f"{i}. <code>{backup}</code> ({file_size:.2f} KB)\n"
        
        if len(backups) > 20:
            message += f"\n... {to_small_caps('and')} {len(backups) - 20} {to_small_caps('more')}"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        LOGGER.error(f"Error listing backups: {e}")
        await update.message.reply_text(to_small_caps("❌ Error listing backups."))


async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/restore <backup_file> - Restore database from backup (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID:
        await update.message.reply_text(to_small_caps("❌ This command is only for the bot owner."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /restore <backup_file>\nUse /listbackups to see available backups."))
        return
    
    backup_file = context.args[0]
    
    # Security check - only allow files from backup directory
    if '..' in backup_file or '/' in backup_file:
        await update.message.reply_text(to_small_caps("❌ Invalid backup file name."))
        return
    
    file_path = os.path.join(BACKUP_DIR, backup_file)
    
    if not os.path.exists(file_path):
        await update.message.reply_text(to_small_caps(f"❌ Backup file not found: {backup_file}"))
        return
    
    # Confirmation
    await update.message.reply_text(
        f"⚠️ <b>{to_small_caps('WARNING')}</b>\n\n"
        f"{to_small_caps('You are about to restore the database from:')}\n"
        f"<code>{backup_file}</code>\n\n"
        f"{to_small_caps('This will OVERWRITE existing data!')}\n"
        f"{to_small_caps('Type /confirmrestore')} <code>{backup_file}</code> {to_small_caps('to proceed.')}",
        parse_mode='HTML'
    )


async def confirmrestore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/confirmrestore <backup_file> - Confirm database restore (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID:
        await update.message.reply_text(to_small_caps("❌ This command is only for the bot owner."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /confirmrestore <backup_file>"))
        return
    
    backup_file = context.args[0]
    
    # Security check
    if '..' in backup_file or '/' in backup_file:
        await update.message.reply_text(to_small_caps("❌ Invalid backup file name."))
        return
    
    file_path = os.path.join(BACKUP_DIR, backup_file)
    
    if not os.path.exists(file_path):
        await update.message.reply_text(to_small_caps(f"❌ Backup file not found: {backup_file}"))
        return
    
    status_message = await update.message.reply_text(to_small_caps("🔄 Restoring database..."))
    
    try:
        # Load backup
        with open(file_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Restore each collection
        restored = 0
        for coll_name, data in backup_data.get("collections", {}).items():
            collection = db[coll_name]
            
            # Clear existing data
            await collection.delete_many({})
            
            # Insert backup data
            documents = data.get("documents", [])
            if documents:
                await collection.insert_many(documents)
                restored += len(documents)
        
        await status_message.edit_text(
            f"✅ <b>{to_small_caps('Restore Complete')}</b>\n\n"
            f"📁 {to_small_caps('Backup:')} <code>{backup_file}</code>\n"
            f"📦 {to_small_caps('Documents restored:')} {restored:,}\n"
            f"🕐 {to_small_caps('Timestamp:')} {backup_data.get('timestamp', 'Unknown')}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"Database restored from: {backup_file} ({restored} documents)")
        
    except Exception as e:
        LOGGER.error(f"Error restoring backup: {e}")
        await status_message.edit_text(to_small_caps(f"❌ Error restoring backup: {str(e)[:100]}"))


async def deletebackup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/deletebackup <backup_file> - Delete a backup file (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /deletebackup <backup_file>"))
        return
    
    backup_file = context.args[0]
    
    # Security check
    if '..' in backup_file or '/' in backup_file:
        await update.message.reply_text(to_small_caps("❌ Invalid backup file name."))
        return
    
    file_path = os.path.join(BACKUP_DIR, backup_file)
    
    if not os.path.exists(file_path):
        await update.message.reply_text(to_small_caps(f"❌ Backup file not found: {backup_file}"))
        return
    
    try:
        os.remove(file_path)
        await update.message.reply_text(
            to_small_caps(f"✅ Backup deleted: {backup_file}")
        )
        LOGGER.info(f"Backup deleted: {backup_file}")
    except Exception as e:
        LOGGER.error(f"Error deleting backup: {e}")
        await update.message.reply_text(to_small_caps(f"❌ Error deleting backup: {str(e)[:100]}"))


# Register handlers
application.add_handler(CommandHandler("backup", backup_cmd, block=False))
application.add_handler(CommandHandler("listbackups", listbackups_cmd, block=False))
application.add_handler(CommandHandler("restore", restore_cmd, block=False))
application.add_handler(CommandHandler("confirmrestore", confirmrestore_cmd, block=False))
application.add_handler(CommandHandler("deletebackup", deletebackup_cmd, block=False))

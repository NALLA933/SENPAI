"""
Eval Module
Developer evaluation commands for debugging and maintenance.
"""

import io
import sys
import traceback
from html import escape
from typing import Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from shivu import application, LOGGER, OWNER_ID, SUDO_USERS
from shivu.utils import to_small_caps


async def eval_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/eval <code> - Execute Python code (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /eval <python_code>"))
        return
    
    code = ' '.join(context.args)
    
    # Create output capture
    stdout = io.StringIO()
    stderr = io.StringIO()
    
    # Prepare environment
    env = {
        'update': update,
        'context': context,
        'bot': context.bot,
        'LOGGER': LOGGER,
    }
    
    # Execute code
    try:
        # Redirect stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr
        
        # Execute
        exec(f"async def __ex():\n" + ''.join(f"    {line}\n" for line in code.split('\n')), env)
        result = await env['__ex']()
        
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Get output
        output = stdout.getvalue()
        errors = stderr.getvalue()
        
        # Build response
        response = f"<b>{to_small_caps('✅ Code Executed')}</b>\n\n"
        
        if result is not None:
            response += f"<b>{to_small_caps('Result:')}</b>\n<pre>{escape(str(result)[:1000])}</pre>\n\n"
        
        if output:
            response += f"<b>{to_small_caps('Output:')}</b>\n<pre>{escape(output[:1000])}</pre>\n\n"
        
        if errors:
            response += f"<b>{to_small_caps('Errors:')}</b>\n<pre>{escape(errors[:1000])}</pre>\n\n"
        
        if not result and not output and not errors:
            response += to_small_caps("(No output)")
        
        await update.message.reply_text(response, parse_mode='HTML')
        
    except Exception as e:
        # Restore stdout and stderr
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr
        
        error_trace = traceback.format_exc()
        await update.message.reply_text(
            f"<b>{to_small_caps('❌ Error')}</b>\n\n"
            f"<pre>{escape(error_trace[:2000])}</pre>",
            parse_mode='HTML'
        )


async def exec_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/exec <code> - Execute Python code without async wrapper (Owner only)."""
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in SUDO_USERS:
        await update.message.reply_text(to_small_caps("❌ This command is only for bot owners."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /exec <python_code>"))
        return
    
    code = ' '.join(context.args)
    
    # Create output capture
    stdout = io.StringIO()
    stderr = io.StringIO()
    
    try:
        # Redirect stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr
        
        # Execute
        exec(code, {'update': update, 'context': context, 'bot': context.bot, 'LOGGER': LOGGER})
        
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Get output
        output = stdout.getvalue()
        errors = stderr.getvalue()
        
        # Build response
        response = f"<b>{to_small_caps('✅ Code Executed')}</b>\n\n"
        
        if output:
            response += f"<b>{to_small_caps('Output:')}</b>\n<pre>{escape(output[:2000])}</pre>\n\n"
        
        if errors:
            response += f"<b>{to_small_caps('Errors:')}</b>\n<pre>{escape(errors[:1000])}</pre>\n\n"
        
        if not output and not errors:
            response += to_small_caps("(No output)")
        
        await update.message.reply_text(response, parse_mode='HTML')
        
    except Exception as e:
        # Restore stdout and stderr
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr
        
        error_trace = traceback.format_exc()
        await update.message.reply_text(
            f"<b>{to_small_caps('❌ Error')}</b>\n\n"
            f"<pre>{escape(error_trace[:2000])}</pre>",
            parse_mode='HTML'
        )


async def shell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shell <command> - Execute shell command (Owner only)."""
    import subprocess
    
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id != OWNER_ID:
        await update.message.reply_text(to_small_caps("❌ This command is only for the bot owner."))
        return
    
    if not context.args:
        await update.message.reply_text(to_small_caps("Usage: /shell <command>"))
        return
    
    command = ' '.join(context.args)
    
    status_message = await update.message.reply_text(to_small_caps("🔄 Executing..."))
    
    try:
        # Execute command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Decode output
        stdout_text = stdout.decode('utf-8', errors='replace')[:2000]
        stderr_text = stderr.decode('utf-8', errors='replace')[:1000]
        
        # Build response
        response = f"<b>{to_small_caps('✅ Command Executed')}</b>\n\n"
        response += f"<code>{escape(command)}</code>\n\n"
        
        if stdout_text:
            response += f"<b>{to_small_caps('Output:')}</b>\n<pre>{escape(stdout_text)}</pre>\n\n"
        
        if stderr_text:
            response += f"<b>{to_small_caps('Errors:')}</b>\n<pre>{escape(stderr_text)}</pre>\n\n"
        
        response += f"{to_small_caps('Exit code:')} {process.returncode}"
        
        await status_message.edit_text(response, parse_mode='HTML')
        
    except Exception as e:
        await status_message.edit_text(
            f"<b>{to_small_caps('❌ Error')}</b>\n\n"
            f"<pre>{escape(str(e))}</pre>",
            parse_mode='HTML'
        )


# Import asyncio for shell command
import asyncio

# Register handlers
application.add_handler(CommandHandler("eval", eval_cmd, block=False))
application.add_handler(CommandHandler("exec", exec_cmd, block=False))
application.add_handler(CommandHandler("shell", shell_cmd, block=False))

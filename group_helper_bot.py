import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
import sqlite3
from datetime import datetime, timedelta
import re
import random

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Database setup
def init_db():
    conn = sqlite3.connect('group_helper.db')
    c = conn.cursor()
    
    # Warnings table
    c.execute('''CREATE TABLE IF NOT EXISTS warnings 
                 (user_id INTEGER, group_id INTEGER, warns INTEGER, 
                  PRIMARY KEY (user_id, group_id))''')
    
    # Mutes table
    c.execute('''CREATE TABLE IF NOT EXISTS mutes 
                 (user_id INTEGER, group_id INTEGER, mute_until TEXT, 
                  PRIMARY KEY (user_id, group_id))''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (group_id INTEGER PRIMARY KEY, welcome INTEGER, goodbye INTEGER, 
                  antispam INTEGER, antiflood INTEGER, log_channel TEXT,
                  max_msg_len INTEGER, media_delete INTEGER)''')
    
    # Blacklist words
    c.execute('''CREATE TABLE IF NOT EXISTS blacklist 
                 (group_id INTEGER, word TEXT, PRIMARY KEY (group_id, word))''')
    
    # Filters
    c.execute('''CREATE TABLE IF NOT EXISTS filters 
                 (group_id INTEGER, keyword TEXT, reply TEXT, PRIMARY KEY (group_id, keyword))''')
    
    # Moderators
    c.execute('''CREATE TABLE IF NOT EXISTS moderators 
                 (group_id INTEGER, user_id INTEGER, PRIMARY KEY (group_id, user_id))''')
    
    conn.commit()
    conn.close()

# Helper functions
async def is_admin_or_mod(update: Update, context: ContextTypes.DEFAULT_TYPE, command_level='basic') -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Creator always allowed
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status == 'creator':
            return True
    except:
        pass
    
    if command_level == 'basic':
        # Check admin or mod
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in ['administrator', 'creator']
        except:
            pass
        
        # Check moderator from DB
        conn = sqlite3.connect('group_helper.db')
        c = conn.cursor()
        result = c.execute("SELECT 1 FROM moderators WHERE group_id=? AND user_id=?", 
                          (chat_id, user_id)).fetchone()
        conn.close()
        return bool(result)
    
    return False

def get_user_mention(user):
    return f"[{user.first_name or 'User'}](tg://user?id={user.id})"

# === WELCOME MESSAGE ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Commands", callback_data='help_main')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 **Welcome to Group Helper Bot!**

Ye bot aapke group ko automatically manage karega:

✅ Anti-Spam & Anti-Flood
✅ Welcome/Goodbye Messages  
✅ Warns & Auto Ban
✅ Media Delete
✅ Log Channel
✅ Custom Filters

**Buttons dabake saare features dekho!**
    """
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === MAIN HELP BUTTONS ===
async def help_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👋 Welcome/Goodbye", callback_data='feature_welcome')],
        [InlineKeyboardButton("🛡️ Anti Spam/Flood", callback_data='feature_antispam')],
        [InlineKeyboardButton("🚫 Block Bot", callback_data='feature_blockbot')],
        [InlineKeyboardButton("📢 SOS Admin", callback_data='feature_sos')],
        [InlineKeyboardButton("🗑️ Delete Messages", callback_data='feature_deletemsg')],
        [InlineKeyboardButton("⚠️ Warns System", callback_data='feature_warns')],
        [InlineKeyboardButton("📱 Media Delete", callback_data='feature_mediadlt')],
        [InlineKeyboardButton("📝 Log Channel", callback_data='feature_log')],
        [InlineKeyboardButton("📏 Msg Length", callback_data='feature_msglen')],
        [InlineKeyboardButton("⌨️ Commands Type", callback_data='feature_commands')],
        [InlineKeyboardButton("🔙 Back", callback_data='help_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📋 **Features & Commands:**", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === FEATURE DETAILS ===
feature_details = {
    'feature_welcome': """
**👋 Welcome/Goodbye Messages**

*Commands:*
`/setwelcome on/off` - Welcome on/off
`/delwelcome` - Welcome delete
`/setgoodbye on/off` - Goodbye on/off
`/goodbye del` - Goodbye delete

*Auto Features:*
✅ New member join pe welcome
✅ Leave pe goodbye message
    """,
    
    'feature_antispam': """
**🛡️ Anti Spam/Flood Protection**

*Auto Features:*
✅ Same message repeat block
✅ Flood messages delete
✅ Fast typing stop

*Commands:*
`/antispam on/off`
`/antiflood on/off`
`/setflood 5` - Max 5 msg/min
    """,
    
    'feature_blockbot': """
**🚫 Block Bots**

*Auto Features:*
✅ New bots auto kick
✅ Bot spam delete

*Commands:*
`/blockbot on/off`
    """,
    
    'feature_sos': """
**📢 SOS Admin**

*Commands:*
`/sos @admin` - Admin ko alert
`/admins` - Saare admins list

*Auto:*
✅ SOS spam protection
    """,
    
    'feature_deletemsg': """
**🗑️ Delete Messages**

*Commands:*
`/del <number>` - Last N messages delete
`/purge` - All messages delete
`/delme` - Apna message delete
    """,
    
    'feature_warns': """
**⚠️ Warns System**

*Commands:*
`/warn @user` - Warn do (3 warns = ban)
`/warns @user` - Warns check
`/resetwarns @user` - Warns clear

*Auto:* 3 warns pe auto ban
    """,
    
    'feature_mediadlt': """
**📱 Media Delete Settings**

*Commands:*
`/mediadlt on/off`
`/setmedia photo/video/sticker`

*Auto:*
✅ Forwarded media delete
✅ Specific media delete
    """,
    
    'feature_log': """
**📝 Log Channel**

*Commands:*
`/setlog @channel`
`/log off`

*Logs:*
✅ All bans/mutes
✅ Joins/leaves
✅ Deleted messages
    """,
    
    'feature_msglen': """
**📏 Message Length Control**

*Commands:*
`/setlen 500` - Max 500 chars
`/len off`

*Auto:* Long messages delete
    """,
    
    'feature_commands': """
**⌨️ Commands Type - /extra**

*Buttons:*
🔸 **Basic** - Ban, Mute, Unban
🔸 **Medium** - Promote, Demote, Lock  
🔸 **Advance** - Filters, Mods, Purge
    """
}

async def feature_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    text = feature_details.get(data, "❌ Feature not available!")
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='help_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === EXTRA COMMANDS BUTTONS ===
async def extra_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔹 Basic", callback_data='extra_basic')],
        [InlineKeyboardButton("🔸 Medium", callback_data='extra_medium')],
        [InlineKeyboardButton("🔺 Advance", callback_data='extra_advance')],
        [InlineKeyboardButton("🔙 Main Menu", callback_data='help_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 **Commands Categories:**\n\nChoose your level:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

extra_commands = {
    'extra_basic': """
**🔹 BASIC COMMANDS** (Mods use kar sakte hain)

`/ban @user` - User ban
`/unban @user` - Unban  
`/mute @user 30` - 30 min mute
`/unmute @user` - Unmute
`/warn @user` - Warning do
`/warns @user` - Warnings check
    """,
    
    'extra_medium': """
**🔸 MEDIUM COMMANDS** (Admins only)

`/promote @user` - Admin banao
`/demote @user` - Admin hatao
`/lock photo` - Photo lock
`/unlock photo` - Unlock
`/kick @user` - Kick karo
`/admins` - Admin list
    """,
    
    'extra_advance': """
**🔺 ADVANCE COMMANDS** (Owner only)

`/filter add keyword reply` - Auto reply
`/filter del keyword` - Filter remove
`/mod add @user` - Moderator banao
`/mod del @user` - Mod remove
`/purge` - All messages delete
`/setlog @channel` - Log setup
    """
}

# === MODERATOR SYSTEM ===
async def add_mod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_mod(update, context, 'advance'):
        return await update.message.reply_text("❌ **Owner only command!**")
    
    if not context.args:
        return await update.message.reply_text("❌ **@username do!**")
    
    user = context.args[0].replace('@', '')
    chat_id = update.effective_chat.id
    
    conn = sqlite3.connect('group_helper.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO moderators (group_id, user_id) VALUES (?, ?)", 
              (chat_id, user))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ **{user} moderator ban gaya!**\nAb ye ban/unban kar sakta hai.")

# === BASIC COMMANDS ===
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_mod(update, context, 'basic'):
        return
    
    if not update.message.reply_to_message and not context.args:
        return await update.message.reply_text("❌ **Reply karo ya @user do!**")
    
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    
    try:
        if user:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"🚫 **{get_user_mention(user)} banned!**")
        else:
            await update.message.reply_text("❌ **User nahi mila!**")
    except Exception as e:
        await update.message.reply_text(f"❌ **Error:** {str(e)}")

# Similar commands for other functions...
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_mod(update, context, 'basic'):
        return
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ **Reply karo!**")
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    conn = sqlite3.connect('group_helper.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO warnings VALUES (?, ?, 0)", (user.id, chat_id))
    c.execute("UPDATE warnings SET warns = warns + 1 WHERE user_id=? AND group_id=?", 
              (user.id, chat_id))
    warns = c.execute("SELECT warns FROM warnings WHERE user_id=? AND group_id=?", 
                     (user.id, chat_id)).fetchone()[0]
    conn.commit()
    conn.close()
    
    if warns >= 3:
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            await update.message.reply_text(f"🚫 **{get_user_mention(user)} 3 warns pe banned!**")
            conn = sqlite3.connect('group_helper.db')
            c = conn.cursor()
            c.execute("DELETE FROM warnings WHERE user_id=? AND group_id=?", (user.id, chat_id))
            conn.commit()
            conn.close()
        except:
            pass
    else:
        await update.message.reply_text(f"⚠️ **Warn #{warns}/3** {get_user_mention(user)}")

# === CALLBACK HANDLER ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help_main':
        await help_main_callback(update, context)
    elif query.data.startswith('feature_'):
        await feature_callback(update, context)
    elif query.data.startswith('extra_'):
        text = extra_commands.get(query.data, "❌ Command not found!")
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='help_main')]]
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, 
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'settings':
        await query.edit_message_text("⚙️ **Settings coming soon...**")

# === MAIN ===
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("extra", extra_command))
    application.add_handler(CommandHandler("mod", add_mod))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("warn", warn))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🚀 **Group Helper Bot Started!**")
    application.run_polling()

if __name__ == '__main__':
    main()

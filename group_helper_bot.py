import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import re
import random
from collections import defaultdict, deque

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "8674805097:AAH6Wgg5akr7TC7fLSeZFiMCtfTe5t7Kcgs"

# In-memory storage (restart pe reset ho jayega)
group_settings = defaultdict(lambda: {
    'welcome': True,
    'goodbye': True,
    'antispam': True,
    'antiflood': True,
    'blockbot': True,
    'max_msg_len': 1000,
    'media_delete': True
})

user_messages = defaultdict(lambda: defaultdict(deque))  # Antiflood tracking
user_warns = defaultdict(lambda: defaultdict(int))      # Warnings
muted_users = defaultdict(lambda: {})                  # Mutes
moderators = defaultdict(set)                          # Moderator list

# Helper functions
async def is_admin_or_mod(update: Update, context: ContextTypes.DEFAULT_TYPE, command_level='basic') -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ['creator', 'administrator']:
            return True
    except:
        pass
    
    # Check moderator
    if command_level == 'basic' and user_id in moderators[chat_id]:
        return True
    
    return False

def get_user_mention(user):
    return f"[{user.first_name or 'User'}](tg://user?id={user.id})"

# === WELCOME SCREEN ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Commands", callback_data='help_main')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 **Welcome to Group Helper Bot!**

*No Database - Super Fast! ⚡*

**Features:**
✅ Anti-Spam & Anti-Flood
✅ Welcome/Goodbye Messages  
✅ Warns System (3 = Auto Ban)
✅ Media Delete Control
✅ Moderator System
✅ Beautiful Buttons

**Buttons se explore karo! 👇**
    """
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === MAIN HELP BUTTONS (11 Buttons) ===
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
        [InlineKeyboardButton("🔙 Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📋 **All Features & Commands:**", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === FEATURE DETAILS ===
feature_details = {
    'feature_welcome': """
**👋 Welcome/Goodbye Messages**

*Commands:*
`/welcome on/off` - Welcome toggle
`/goodbye on/off` - Goodbye toggle

*Auto Features:* ✅
- New join pe welcome
- Leave pe goodbye
    """,

    'feature_antispam': """
**🛡️ Anti Spam/Flood**

*Auto Features:* ✅
- Same message repeat
- Flood messages delete  
- Fast typing stop

*Commands:*
`/antispam on/off`
`/antiflood on/off`
    """,

    'feature_blockbot': """
**🚫 Block Bots**

*Auto Features:* ✅
- New bots auto kick
- Bot spam delete

*Commands:*
`/blockbot on/off`
    """,

    'feature_sos': """
**📢 SOS Admin**

*Commands:*
`/sos` - Admin ko alert
`/admins` - Admin list
    """,

    'feature_deletemsg': """
**🗑️ Delete Messages**

*Commands:*
`/del 10` - Last 10 delete
`/purge` - All delete (Admin)
`/delme` - Apna message delete
    """,

    'feature_warns': """
**⚠️ Warns System**

*Commands:*
`/warn @user` - Warning (3 = Ban)
`/warns @user` - Check warns
`/resetwarns @user` - Clear warns

*Auto:* 3 warns = 🚫 Ban
    """,

    'feature_mediadlt': """
**📱 Media Delete**

*Commands:*
`/mediadlt on/off`
`/setmedia photo|video|gif`

*Auto:* Forwarded media delete
    """,

    'feature_log': """
**📝 Log Channel** *(Coming Soon)*
    """,

    'feature_msglen': """
**📏 Message Length**

*Commands:*
`/setlen 500` - Max 500 chars
`/len off` - Disable

*Auto:* Long msg delete
    """,

    'feature_commands': """
**⌨️ Commands - /extra**

*3 Levels:*
🔹 **Basic** - ban/mute/warn
🔸 **Medium** - promote/lock/kick
🔺 **Advance** - mod/filter/purge
    """
}

# === /EXTRA COMMAND ===
async def extra_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔹 BASIC", callback_data='extra_basic')],
        [InlineKeyboardButton("🔸 MEDIUM", callback_data='extra_medium')],
        [InlineKeyboardButton("🔺 ADVANCE", callback_data='extra_advance')],
        [InlineKeyboardButton("🏠 Home", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 **Commands by Level:**\n*Choose your commands:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

extra_commands = {
    'extra_basic': """
**🔹 BASIC COMMANDS** *(Mods + Admins)*

- `/ban @user` - Permanent ban
- `/unban @user` - Unban user  
- `/mute @user 30` - 30 min mute
- `/unmute @user` - Unmute
- `/warn @user` - Warning do
- `/warns @user` - Warnings dekho
- `/kick @user` - Kick only
    """,

    'extra_medium': """
**🔸 MEDIUM COMMANDS** *(Admins Only)*

- `/promote @user` - Admin banao
- `/demote @user` - Admin hatao
- `/lock photo|video|sticker` - Lock
- `/unlock photo|video|sticker` - Unlock
- `/admins` - Admin list
- `/pin` - Message pin karo
    """,

    'extra_advance': """
**🔺 ADVANCE COMMANDS** *(Owner Only)*

- `/mod add @user` - Moderator banao
- `/mod del @user` - Mod hatao
- `/filter add keyword reply` - Auto reply
- `/filter del keyword` - Filter remove
- `/purge` - All messages delete
- `/setwelcome text` - Custom welcome
    """
}

# === MODERATOR SYSTEM ===
async def mod_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_mod(update, context, 'advance'):
        return await update.message.reply_text("❌ **Owner only!**")
    
    chat_id = update.effective_chat.id
    
    if context.args and context.args[0] == 'add':
        if len(context.args) < 2:
            return await update.message.reply_text("❌ **/mod add @username**")
        
        mod_user = context.args[1].replace('@', '')
        moderators[chat_id].add(int(mod_user))
        await update.message.reply_text(f"✅ **{mod_user} Moderator ban gaya!**\nBan/Unban use kar sakta hai.")
    
    elif context.args and context.args[0] == 'del':
        if len(context.args) < 2:
            return await update.message.reply_text("❌ **/mod del @username**")
        
        mod_user = context.args[1].replace('@', '')
        moderators[chat_id].discard(int(mod_user))
        await update.message.reply_text(f"✅ **{mod_user} se moderator hataya!**")

# === BASIC COMMANDS ===
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_mod(update, context, 'basic'):
        return await update.message.reply_text("❌ **Mod/Admin only!**")
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ **User ko reply karo!**")
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, user.id)
        await update.message.reply_text(f"🚫 **{get_user_mention(user)} banned!**", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ **Ban failed:** {str(e)}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_mod(update, context, 'basic'):
        return await update.message.reply_text("❌ **Mod/Admin only!**")
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ **User ko reply karo!**")
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    user_warns[chat_id][user.id] += 1
    warns_count = user_warns[chat_id][user.id]
    
    msg = f"⚠️ **Warn #{warns_count}/3** {get_user_mention(user)}"
    
    if warns_count >= 3:
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            msg += "\n🚫 **3 warns complete - BANNED!**"
            del user_warns[chat_id][user.id]  # Reset warns
        except:
            pass
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ **User ko reply karo!**")
    
    user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    count = user_warns[chat_id].get(user.id, 0)
    
    await update.message.reply_text(f"📊 **Warnings:** {count}/3")

# === CALLBACK HANDLER ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'help_main':
        await help_main_callback(update, context)
    elif data == 'start':
        await start(update, context)
    elif data.startswith('feature_'):
        text = feature_details.get(data, "❌ Feature nahi mila!")
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='help_main')]]
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, 
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith('extra_'):
        text = extra_commands.get(data, "❌ Command nahi mila!")
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='help_main')]]
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

# === MAIN ===
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command Handlers
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("extra", extra_command))
    application.add_handler(CommandHandler("mod", mod_command))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("warns", warns))
    
    # Button Handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🚀 **Database-Free Group Helper Bot Started! ⚡**")
    print("✅ No SQLite - Pure Memory Storage")
    application.run_polling()

if __name__ == '__main__':
    main()

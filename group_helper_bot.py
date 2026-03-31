import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from collections import defaultdict
import re

# Config
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
logging.basicConfig(level=logging.INFO)

# Storage (No Database)
group_settings = defaultdict(dict)
user_data = defaultdict(dict)

# Helper Functions
async def is_admin(chat_id, user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def get_group_name(chat):
    return chat.title or chat.first_name or "Group"

# === /START COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Add Me To Group", url="https://t.me/YOUR_BOT_USERNAME?startgroup=true")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
🤖 **Welcome to Group Helper Bot!**

/help - Commands dekho

**Features:**
✅ Anti-Spam/Flood
✅ Welcome Messages
✅ Media Control
✅ Much More...
    """
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup, disable_web_page_preview=True)

# === /HELP COMMAND ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    is_group = update.effective_chat.type in ['group', 'supergroup']
    
    keyboard = [
        [InlineKeyboardButton("🔹 Basic Commands", callback_data="help_basic")],
        [InlineKeyboardButton("🔸 Advance", callback_data="help_advance")],
        [InlineKeyboardButton("🔺 Expert", callback_data="help_expert")]
    ]
    
    if is_group:
        keyboard.append([InlineKeyboardButton("💬 Go To Chat", callback_data="go_to_chat")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "**Welcome to Help Menu**"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === HELP CALLBACKS ===
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help_basic":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        text = """
**🔹 BASIC COMMANDS:**
/reload - Bot restart
/ban - User ban
/mute - User mute
/kick - User kick
/unban - Unban
/info - User info
/staff - Staff list
        """
    
    elif data == "help_advance":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        text = """
**🔸 ADVANCE COMMANDS:**
/warn - Warning do
/unwarn - Warn hatao
/warns - Warns check
/delwarns - All warns clear
/del - Selected msg delete
        """
    
    elif data == "help_expert":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        text = """
**🔺 EXPERT COMMANDS:**
/pin [message] - Pin message
/pin - Reply se pin
/delpin - Pinned delete
/editpin - Pinned edit
        """
    
    elif data == "help_main":
        await help_command(update, context)
        return
    
    elif data == "go_to_chat":
        keyboard = [[InlineKeyboardButton("💬 Open Help", url=f"https://t.me/{context.bot.username}?start=help")]]
        await query.edit_message_text("💬 **Bot ke DM me jao Help ke liye**", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === SETTINGS SYSTEM ===
async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query if update.callback_query else None
    chat_id = update.effective_chat.id
    
    if not await is_admin(chat_id, update.effective_user.id, context):
        text = "❌ **Group me /settings use karo (Admin hoke)!**"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="settings_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Open Here", callback_data="settings_open_here")],
        [InlineKeyboardButton("💬 Open in Pvt", callback_data="settings_pvt")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "**Use in Group:** `/settings`"
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def settings_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not await is_admin(chat_id, update.effective_user.id, context):
        await update.message.reply_text("❌ **Admin only!**")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Open Here", callback_data=f"settings_open_{chat_id}")],
        [InlineKeyboardButton("💬 Open in Pvt", callback_data="settings_pvt")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("**Choose:**", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === MAIN SETTINGS MENU ===
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    group_name = get_group_name(update.effective_chat)
    
    text = f"""
**⚙️ Settings**

**Group:** `{group_name}`

**Select one of the settings you want to change:**
    """
    
    keyboard = [
        [InlineKeyboardButton("📜 Regulation", callback_data="set_regulation")],
        [InlineKeyboardButton("🛡️ Anti Spam", callback_data="set_antispam")],
        [InlineKeyboardButton("👋 Welcome", callback_data="set_welcome")],
        [InlineKeyboardButton("🌊 AntiFlood", callback_data="set_antiflood")],
        [InlineKeyboardButton("🤖 Bot Block", callback_data="set_botblock")],
        [InlineKeyboardButton("📱 Media", callback_data="set_media")],
        [InlineKeyboardButton("✅ Approval", callback_data="set_approval")],
        [InlineKeyboardButton("⌨️ Commands", callback_data="set_commands")],
        [InlineKeyboardButton("❌ Close", callback_data="close_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === REGULATION SETTINGS ===
async def regulation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**📜 Regulation**

From this menu you can manage group rules that will be shown with `/rules`
    """
    keyboard = [[InlineKeyboardButton("💬 Customize Messages", callback_data="reg_custom")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def reg_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**💬 Customize Messages**

**Send now the message you want to set**
    """
    keyboard = [
        [InlineKeyboardButton("🗑️ Remove Message", callback_data="reg_remove")],
        [InlineKeyboardButton("🔙 Back", callback_data="set_regulation")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === ANTI SPAM ===
async def antispam_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**🛡️ Anti Spam**

In this menu you can decide whether to protect your groups from links, forwarding
    """
    keyboard = [
        [InlineKeyboardButton("✅ Turn ON", callback_data="antispam_on")],
        [InlineKeyboardButton("❌ Turn OFF", callback_data="antispam_off")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === WELCOME SETTINGS ===
async def welcome_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**👋 Welcome**

From this menu you can set a welcome msg that will be sent when someone joins
    """
    keyboard = [
        [InlineKeyboardButton("✅ Turn ON", callback_data="welcome_on")],
        [InlineKeyboardButton("❌ Turn OFF", callback_data="welcome_off")],
        [InlineKeyboardButton("✍️ Customize Msg", callback_data="welcome_custom")],
        [InlineKeyboardButton("🗑️ Delete Last Msg", callback_data="welcome_del")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === ANTIFLOOD ===
async def antiflood_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**🌊 AntiFlood**

Set punishment for users who send many messages in short time
    """
    keyboard = [
        [InlineKeyboardButton("📨 Messages", callback_data="flood_msg")],
        [InlineKeyboardButton("⏱️ Time", callback_data="flood_time")],
        [InlineKeyboardButton("🔇 Mute", callback_data="flood_mute")],
        [InlineKeyboardButton("🚫 Ban", callback_data="flood_ban")],
        [InlineKeyboardButton("🗑️ Delete Msg", callback_data="flood_del")],
        [InlineKeyboardButton("✅ Tick", callback_data="flood_tick")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === NUMBER SELECTOR ===
def number_keyboard(back_data):
    keyboard = []
    for i in range(2, 11, 2):
        keyboard.append([InlineKeyboardButton(str(i), callback_data=f"{back_data}_{i}")])
    for i in range(12, 21, 2):
        keyboard.append([InlineKeyboardButton(str(i), callback_data=f"{back_data}_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=back_data.replace("_select", ""))])
    return InlineKeyboardMarkup(keyboard)

# === BOT BLOCK ===
async def botblock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**🤖 Bot Block**

Users won't be able to add bots. Choose penalty:
    """
    keyboard = [
        [InlineKeyboardButton("✅ Enable", callback_data="botblock_on")],
        [InlineKeyboardButton("❌ Disable", callback_data="botblock_off")],
        [InlineKeyboardButton("🔇 Mute", callback_data="botblock_mute")],
        [InlineKeyboardButton("🚫 Ban", callback_data="botblock_ban")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === MEDIA SETTINGS ===
async def media_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**📱 Media Block**

Block media in group. Use `/filters` to customize
    """
    keyboard = [
        [InlineKeyboardButton("🖼️ Photo ✅/❌", callback_data="media_photo")],
        [InlineKeyboardButton("🎥 Video ✅/❌", callback_data="media_video")],
        [InlineKeyboardButton("🎡 GIF ✅/❌", callback_data="media_gif")],
        [InlineKeyboardButton("✨ Sticker ✅/❌", callback_data="media_sticker")],
        [InlineKeyboardButton("🎭 Ani Sticker ✅/❌", callback_data="media_anisticker")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === APPROVAL MODE ===
async def approval_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**✅ Approval Mode**

Delegate group approvals to bot for link joiners
    """
    keyboard = [
        [InlineKeyboardButton("✅ Turn ON", callback_data="approval_on")],
        [InlineKeyboardButton("❌ Turn OFF", callback_data="approval_off")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === COMMANDS PREFIX ===
async def commands_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """
**⌨️ Commands Prefix**

Set bot trigger prefix
    """
    keyboard = [
        [InlineKeyboardButton("/", callback_data="prefix_slash")],
        [InlineKeyboardButton("!/", callback_data="prefix_exclam")],
        [InlineKeyboardButton(".;", callback_data="prefix_dot")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_menu")]
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# === MAIN CALLBACK HANDLER ===
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat.id
    
    if data == "settings_start":
        await settings_start(update, context)
    
    elif data.startswith("settings_open_"):
        await settings_menu(update, context)
    
    elif data == "settings_pvt":
        keyboard = [[InlineKeyboardButton("💬 Go To Chat", url=f"https://t.me/{context.bot.username}?start=settings")]]
        await query.edit_message_text("💬 **DM me Settings ke liye jao**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "set_regulation":
        await regulation_menu(update, context)
    
    elif data == "reg_custom":
        await reg_custom(update, context)
    
    elif data == "set_antispam":
        await antispam_menu(update, context)
    
    elif data == "set_welcome":
        await welcome_menu(update, context)
    
    elif data == "set_antiflood":
        await antiflood_menu(update, context)
    
    elif data.startswith("flood_") or data.startswith("msg_select_") or data.startswith("time_select_"):
        # Handle number selection
        await query.answer("✅ Set!")
    
    elif data == "set_botblock":
        await botblock_menu(update, context)
    
    elif data == "set_media":
        await media_menu(update, context)
    
    elif data == "set_approval":
        await approval_menu(update, context)
    
    elif data == "set_commands":
        await commands_menu(update, context)
    
    elif data == "settings_menu":
        await settings_menu(update, context)
    
    elif data == "close_settings":
        await query.edit_message_text("✅ **Settings Closed!**")
    
    else:
        await help_callback(update, context)

# === GROUP ADD HANDLER ===
async def group_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("📋 Open Here", callback_data=f"settings_open_{chat_id}")],
        [InlineKeyboardButton("💬 Open in Pvt", callback_data="settings_pvt")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("**⚙️ Settings:**", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# === SETTINGS COMMAND ===
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await settings_group(update, context)

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_cmd))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_add_handler))
    
    print("🚀 **Group Helper Bot Started! (No DB)**")
    app.run_polling()

if __name__ == "__main__":
    main()

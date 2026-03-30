import requests
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8664283727:AAG1EEFyCFFio3ll6qfxHKTMP18Jedq4ZPI"
GITHUB_TOKEN = "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"

headers = {"Authorization": f"token {GITHUB_TOKEN}"}
user_repo = {}

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Ready!\n\n"
        "/repo username/repo\n"
        "/files - show all files"
    )

# SET REPO
async def set_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: /repo username/repo")
        return
    user_repo[update.message.from_user.id] = context.args[0]
    await update.message.reply_text("✅ Repo selected")

# LIST FILES
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_repo:
        await update.message.reply_text("❌ Set repo first")
        return

    repo = user_repo[user_id]
    url = f"https://api.github.com/repos/{repo}/contents/"

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        await update.message.reply_text("❌ Failed to fetch files")
        return

    files = res.json()
    buttons = []

    for f in files:
        if f["type"] == "file":
            buttons.append([InlineKeyboardButton(f["name"], callback_data=f"file|{f['name']}")])

    if not buttons:
        await update.message.reply_text("❌ No files found")
        return

    await update.message.reply_text(
        "📂 Select file:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# FILE ACTION MENU
async def file_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filename = query.data.split("|")[1]

    buttons = [
        [InlineKeyboardButton("🗑 Delete", callback_data=f"delete|{filename}")],
        [InlineKeyboardButton("♻️ Update", callback_data=f"update|{filename}")]
    ]

    await query.message.reply_text(
        f"⚙️ {filename}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# DELETE FILE
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filename = query.data.split("|")[1]
    user_id = query.from_user.id

    if user_id not in user_repo:
        await query.message.reply_text("❌ Repo not set")
        return

    repo = user_repo[user_id]
    url = f"https://api.github.com/repos/{repo}/contents/{filename}"

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        await query.message.reply_text("❌ File not found")
        return

    sha = res.json()["sha"]

    data = {"message": f"Delete {filename}", "sha": sha}
    r = requests.delete(url, json=data, headers=headers)

    await query.message.reply_text("🗑 Deleted" if r.status_code == 200 else "❌ Failed")

# ASK UPDATE
async def ask_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filename = query.data.split("|")[1]
    context.user_data["update_file"] = filename

    await query.message.reply_text(f"📤 Send new file for {filename}")

# HANDLE UPLOAD / UPDATE
async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_repo:
        await update.message.reply_text("❌ Set repo first")
        return

    file = await update.message.document.get_file()
    file_data = await file.download_as_bytearray()

    repo = user_repo[user_id]
    filename = context.user_data.get("update_file", update.message.document.file_name)

    url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    content = base64.b64encode(file_data).decode()

    res = requests.get(url, headers=headers)

    if res.status_code == 200:
        sha = res.json()["sha"]
        data = {
            "message": f"Update {filename}",
            "content": content,
            "sha": sha
        }
    else:
        data = {
            "message": f"Upload {filename}",
            "content": content
        }

    r = requests.put(url, json=data, headers=headers)

    await update.message.reply_text("✅ Done" if r.status_code in [200, 201] else "❌ Error")

# RUN BOT
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("repo", set_repo))
app.add_handler(CommandHandler("files", list_files))

app.add_handler(CallbackQueryHandler(file_action, pattern="^file"))
app.add_handler(CallbackQueryHandler(delete_file, pattern="^delete"))
app.add_handler(CallbackQueryHandler(ask_update, pattern="^update"))

app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))

print("🔥 Bot running...")
app.run_polling()

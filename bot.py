from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import sqlite3

# ---------- TOKEN VA OWNER ----------
OWNER_ID = 1373647
BOT_TOKEN = "8332135205:AAF2RbOWLE9elxsmFT9fh12IqYnjqPwwHrg"
BOT_USERNAME = "@kinoni_izlabot"

# ---------- DATABASE ----------
conn = sqlite3.connect("kino_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    extra_text TEXT DEFAULT ''
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    channel TEXT PRIMARY KEY
)
""")
conn.commit()

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    if user_id == OWNER_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        keyboard = [
            [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
            [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 Kanalni o‘chirish", callback_data="delete_channel")],
            [InlineKeyboardButton("📋 Kanallar ro‘yxati", callback_data="list_channels")],
            [InlineKeyboardButton("📝 Qo‘shimcha matn", callback_data="manage_text")],
            [InlineKeyboardButton(f"👥 Foydalanuvchilar soni: {total_users}", callback_data="user_count")]
        ]
        await update.message.reply_text("Salom Owner! Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Salom! Kino kodi kiriting:")

# ---------- CALLBACK HANDLER ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if user_id != OWNER_ID:
        return

    if data == "broadcast":
        context.user_data["action"] = "broadcast"
        await query.message.reply_text("Broadcast xabarni yozing (matn, video yoki rasm):")
        return

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if not update.message.video:
        return
    context.user_data["video_file_id"] = update.message.video.file_id
    context.user_data["action"] = "set_code"
    await update.message.reply_text("Endi video uchun kodi yozing:")

# ---------- BROADCAST HANDLER (caption bilan ishlaydi) ----------
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("action")
    if action != "broadcast":
        return

    text = update.message.caption if update.message.caption else (update.message.text if update.message.text else "")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    count = 0

    for u in users:
        try:
            if update.message.video:
                await context.bot.send_video(u[0], update.message.video.file_id, caption=text)
            elif update.message.photo:
                # Telegramda photo bir nechta variantda keladi, oxirgi elementni olish yaxshiroq
                photo_file_id = update.message.photo[-1].file_id
                await context.bot.send_photo(u[0], photo_file_id, caption=text)
            elif update.message.text:
                await context.bot.send_message(u[0], text)
            count += 1
        except:
            pass

    await update.message.reply_text(f"Xabar {count} foydalanuvchiga yuborildi!")
    context.user_data.clear()

# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")

    if user_id == OWNER_ID:
        if action == "set_code":
            file_id = context.user_data.get("video_file_id")
            cursor.execute("INSERT OR REPLACE INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()
            await update.message.reply_video(file_id, caption=f"Kod: {text}\n{BOT_USERNAME}")
            await update.message.reply_text(f"Video saqlandi! Kod: {text}")
            context.user_data.clear()
            return

# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT, handle_broadcast))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()

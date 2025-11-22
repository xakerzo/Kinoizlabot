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

    # OWNER TUGMALAR
    if data == "upload_video":
        context.user_data["action"] = "upload_video"
        await query.message.reply_text("Video yuboring va keyin kodi yozing:")
        return
    elif data == "broadcast":
        context.user_data["action"] = "broadcast"
        await query.message.reply_text("Broadcast xabarni yozing (matn, video yoki rasm):")
        return
    elif data == "add_channel":
        context.user_data["action"] = "add_channel"
        await query.message.reply_text("Kanal nomini yozing (masalan @kanal_nomi):")
        return
    elif data == "delete_channel":
        context.user_data["action"] = "delete_channel"
        await query.message.reply_text("O‘chiriladigan kanal nomini yozing:")
        return
    elif data == "list_channels":
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        if channels:
            text = "Kanallar ro‘yxati:\n" + "\n".join([c[0] for c in channels])
        else:
            text = "Hali kanal qo‘shilmagan."
        await query.message.reply_text(text)
        return
    elif data == "manage_text":
        keyboard = [
            [InlineKeyboardButton("➕ Qo‘shish", callback_data="add_extra")],
            [InlineKeyboardButton("🔍 Tekshirish", callback_data="check_extra")],
            [InlineKeyboardButton("🗑 O‘chirish", callback_data="delete_extra")]
        ]
        await query.message.reply_text("Video tagidagi qo‘shimcha matnni boshqarish:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data == "add_extra":
        context.user_data["action"] = "add_extra"
        await query.message.reply_text("Matnni yozing, u barcha videolarga qo‘shiladi:")
        return
    elif data == "check_extra":
        cursor.execute("SELECT code, extra_text FROM films")
        films = cursor.fetchall()
        if films:
            msg = "Videolar va qo‘shimcha matn:\n"
            for f in films:
                msg += f"Kod: {f[0]}, Matn: {f[1]}\n"
            await query.message.reply_text(msg)
        else:
            await query.message.reply_text("Hali videolar yo‘q.")
        return
    elif data == "delete_extra":
        cursor.execute("UPDATE films SET extra_text=''")
        conn.commit()
        await query.message.reply_text("Qo‘shimcha matn barcha videolardan o‘chirildi!")
        context.user_data.clear()
        return
    elif data.startswith("update_"):
        old_code = data.split("_")[1]
        context.user_data["action"] = "update_code"
        context.user_data["old_code"] = old_code
        await query.message.reply_text(f"Yangi kodni yozing (eski kod: {old_code}):")
        return
    elif data.startswith("delete_"):
        code = data.split("_")[1]
        cursor.execute("DELETE FROM films WHERE code=?", (code,))
        conn.commit()
        await query.message.reply_text(f"Video {code} o‘chirildi!")
        return
    elif data == "user_count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        await query.message.reply_text(f"Hozirgi foydalanuvchilar soni: {total_users}")
        return

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return

    if update.message.video:
        action = context.user_data.get("action")
        if action == "upload_video":
            context.user_data["video_file_id"] = update.message.video.file_id
            context.user_data["action"] = "set_code"
            await update.message.reply_text("Endi video uchun kodi yozing:")

# ---------- BROADCAST HANDLER ----------
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
        # Video kodi qo‘shish
        if action == "set_code":
            cursor.execute("SELECT * FROM films WHERE code=?", (text,))
            if cursor.fetchone():
                await update.message.reply_text("Ushbu kod allaqachon mavjud! Iltimos boshqa kod yozing.")
                return

            file_id = context.user_data.get("video_file_id")
            cursor.execute("INSERT INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ Videoni o‘chirish", callback_data=f"delete_{text}")]
            ]
            await update.message.reply_video(file_id, caption=f"Kod: {text}\n{BOT_USERNAME}", reply_markup=InlineKeyboardMarkup(keyboard))
            await update.message.reply_text(f"Video saqlandi! Kod: {text}")
            context.user_data.clear()
            return

        # Kod yangilash
        elif action == "update_code":
            old_code = context.user_data.get("old_code")
            cursor.execute("SELECT * FROM films WHERE code=?", (text,))
            if cursor.fetchone():
                await update.message.reply_text("Ushbu kod allaqachon mavjud! Iltimos boshqa kod yozing.")
                return
            cursor.execute("UPDATE films SET code=? WHERE code=?", (text, old_code))
            conn.commit()
            cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (text,))
            result = cursor.fetchone()
            if result:
                file_id, extra_text = result
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                     InlineKeyboardButton("❌ Videoni o‘chirish", callback_data=f"delete_{text}")]
                ]
                await update.message.reply_video(file_id, caption=f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}", reply_markup=InlineKeyboardMarkup(keyboard))
                await update.message.reply_text(f"Video kodi yangilandi! Yangi kod: {text}")
            context.user_data.clear()
            return

        # Broadcast
        elif action == "broadcast":
            await handle_broadcast(update, context)
            return

        # Kanal qo‘shish
        elif action == "add_channel":
            cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            conn.commit()
            await update.message.reply_text(f"Kanal qo‘shildi: {text}")
            context.user_data.clear()
            return

        # Kanal o‘chirish
        elif action == "delete_channel":
            cursor.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text(f"Kanal o‘chirildi: {text}")
            context.user_data.clear()
            return

        # Qo‘shimcha matn
        elif action == "add_extra":
            cursor.execute("UPDATE films SET extra_text=?", (text,))
            conn.commit()
            await update.message.reply_text("Qo‘shimcha matn barcha videolarga qo‘shildi!")
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

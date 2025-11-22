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

# Jadval yaratish
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

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    if user_id == OWNER_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        keyboard = [
            [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
            [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 Kanalni o‘chirish", callback_data="delete_channel")],
            [InlineKeyboardButton("📋 Kanallar ro‘yxati", callback_data="list_channels")],
            [InlineKeyboardButton("📝 Qo‘shimcha matn", callback_data="manage_text")]
        ]
        await update.message.reply_text(
            f"Salom Owner! Foydalanuvchilar soni: {user_count}\nTanlang:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("Salom! Kino kodi kiriting:")

# ---------- CALLBACK HANDLER ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # ---------- FOYDALANUVCHI OBUNA TEKSHIRISH ----------
    if data.startswith("check_subs_"):
        code = data.split("_")[-1]
        cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (code,))
        result = cursor.fetchone()
        if not result:
            await query.message.reply_text("Bunday kodga film topilmadi!")
            return
        file_id, extra_text = result

        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        not_subscribed = []

        for c in channels:
            try:
                member = await context.bot.get_chat_member(c[0], user_id)
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(c[0])
            except:
                not_subscribed.append(c[0])

        if not_subscribed:
            keyboard = [[InlineKeyboardButton(f"✅ Obuna bo‘lish: {ch}", url=f"https://t.me/{ch[1:]}")] for ch in not_subscribed]
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{code}")])
            await query.message.reply_text(
                "Iltimos, kinoni ko‘rishdan oldin quyidagi kanallarga obuna bo‘ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{code}"),
                 InlineKeyboardButton("❌ Videoni o‘chirish", callback_data=f"delete_{code}")]
            ]
            await query.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
        return

    # ---------- OWNER TUGMALAR ----------
    if user_id != OWNER_ID:
        return

    if data == "upload_video":
        context.user_data["action"] = "upload_video"
        await query.message.reply_text("Video yuboring va keyin kodi yozing:")
        return

    elif data == "search_video":
        context.user_data["action"] = "search_video"
        await query.message.reply_text("Qidiriladigan kodni yozing:")
        return

    elif data == "broadcast":
        context.user_data["action"] = "broadcast"
        keyboard = [
            [InlineKeyboardButton("📝 Matn yuborish", callback_data="broadcast_text")],
            [InlineKeyboardButton("🖼 Rasm yuborish", callback_data="broadcast_photo")],
            [InlineKeyboardButton("🎥 Video yuborish", callback_data="broadcast_video")]
        ]
        await query.message.reply_text("Broadcast turi tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data.startswith("broadcast_"):
        type_ = data.split("_")[1]
        context.user_data["broadcast_type"] = type_
        if type_ == "text":
            await query.message.reply_text("Broadcast matnini yozing:")
        else:
            await query.message.reply_text(f"Broadcast {type_} yuboring va caption yozing:")
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
        await query.message.reply_text(
            "Video tagidagi qo‘shimcha matnni boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
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
        context.user_data["action"] = "delete_extra"
        await query.message.reply_text("Qo‘shimcha matn barcha videolardan o‘chirildi!")
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

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if not update.message.video and not update.message.photo:
        return
    action = context.user_data.get("action")
    
    if action == "upload_video":
        if update.message.video:
            context.user_data["video_file_id"] = update.message.video.file_id
        elif update.message.photo:
            context.user_data["video_file_id"] = update.message.photo[-1].file_id
        context.user_data["action"] = "set_code"
        await update.message.reply_text("Endi video uchun kodi yozing:")
        return
    if action == "broadcast" and context.user_data.get("broadcast_type") in ["photo", "video"]:
        context.user_data["broadcast_file_id"] = update.message.video.file_id if context.user_data["broadcast_type"] == "video" else update.message.photo[-1].file_id
        context.user_data["action"] = "broadcast_caption"
        await update.message.reply_text("Endi caption yozing:")
        return

# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")

    # ---------- OWNER ACTIONS ----------
    if user_id == OWNER_ID:
        # Video kodi qo‘shish
        if action == "set_code":
            file_id = context.user_data.get("video_file_id")
            cursor.execute("SELECT code FROM films WHERE code=?", (text,))
            if cursor.fetchone():
                await update.message.reply_text("Bu kod band! Iltimos, boshqa kod kiriting.")
                return
            cursor.execute("INSERT INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ Videoni o‘chirish", callback_data=f"delete_{text}")]
            ]
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=f"Kod: {text}\n{BOT_USERNAME}")
            await update.message.reply_text(f"Video saqlandi! Kod: {text}")
            context.user_data.clear()
            return

        # Broadcast caption yozish
        if action == "broadcast_caption":
            context.user_data["broadcast_caption"] = text
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            count = 0
            b_type = context.user_data.get("broadcast_type", "text")
            file_id = context.user_data.get("broadcast_file_id")
            for u in users:
                try:
                    if b_type == "photo":
                        await context.bot.send_photo(u[0], photo=file_id, caption=text)
                    elif b_type == "video":
                        await context.bot.send_video(u[0], video=file_id, caption=text)
                    else:
                        await context.bot.send_message(u[0], text)
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"Xabar {count} foydalanuvchiga yuborildi!")
            context.user_data.clear()
            return

        # Text broadcast
        if action == "broadcast" and context.user_data.get("broadcast_type") == "text":
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            count = 0
            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"Xabar {count} foydalanuvchiga yuborildi!")
            context.user_data.clear()
            return

        # Owner search, add/delete channel, extra text, update code handled in callback
        # ...

    # ---------- FOYDALANUVCHI KINO KO‘RISH ----------
    cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (text,))
    result = cursor.fetchone()
    if result:
        file_id, extra_text = result
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        not_subscribed = []
        for c in channels:
            try:
                member = await context.bot.get_chat_member(c[0], user_id)
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(c[0])
            except:
                not_subscribed.append(c[0])

        if not_subscribed:
            keyboard = [[InlineKeyboardButton(f"✅ Obuna bo‘lish: {ch}", url=f"https://t.me/{ch[1:]}")] for ch in not_subscribed]
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{text}")])
            await update.message.reply_text(
                "Iltimos, kinoni ko‘rishdan oldin quyidagi kanallarga obuna bo‘ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ Videoni o‘chirish", callback_data=f"delete_{text}")]
            ] if user_id == OWNER_ID else None
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, caption=caption_text)
    else:
        await update.message.reply_text("Bunday kodga film topilmadi!")

# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_owner_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_polling()

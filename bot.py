import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ---------- TOKEN VA OWNER (Railway Environment Variable) ----------
BOT_TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
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
        keyboard = [
            [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
            [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 Kanalni o‘chirish", callback_data="delete_channel")],
            [InlineKeyboardButton("📋 Kanallar ro‘yxati", callback_data="list_channels")],
            [InlineKeyboardButton("📝 Qo‘shimcha matn", callback_data="manage_text")]
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

    # -------- FOYDALANUVCHI OBUNA TEKSHIRISH --------
    if data.startswith("check_subs_"):
        code = data.split("_")[-1]
        cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (code,))
        result = cursor.fetchone()

        if not result:
            await query.message.reply_text("Bunday kod topilmadi!")
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
            keyboard = [
                [InlineKeyboardButton(f"Obuna: {ch}", url=f"https://t.me/{ch[1:]}")]
                for ch in not_subscribed
            ]
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{code}")])

            await query.message.reply_text(
                "Quyidagi kanallarga obuna bo‘ling:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            caption = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏ Kodni almashtirish", callback_data=f"update_{code}"),
                 InlineKeyboardButton("❌ O‘chirish", callback_data=f"delete_{code}")]
            ]
            await query.message.reply_video(file_id, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

        return

    # -------- OWNER BO‘LMASA QAYTSIN --------
    if user_id != OWNER_ID:
        return

    # ------- OWNER ACTIONS -------
    if data == "upload_video":
        context.user_data["action"] = "upload_video"
        await query.message.reply_text("Video yuboring, keyin kodi yozing:")
        return

    if data == "search_video":
        context.user_data["action"] = "search_video"
        await query.message.reply_text("Kod kiriting:")
        return

    if data == "broadcast":
        context.user_data["action"] = "broadcast"
        await query.message.reply_text("Xabarni kiriting:")
        return

    if data == "add_channel":
        context.user_data["action"] = "add_channel"
        await query.message.reply_text("Kanal nomi (@ bilan):")
        return

    if data == "delete_channel":
        context.user_data["action"] = "delete_channel"
        await query.message.reply_text("O‘chiradigan kanal nomi:")
        return

    if data == "list_channels":
        cursor.execute("SELECT channel FROM channels")
        ch = cursor.fetchall()
        if ch:
            await query.message.reply_text("Kanallar:\n" + "\n".join([i[0] for i in ch]))
        else:
            await query.message.reply_text("Kanallar qo‘shilmagan.")
        return

    # Qo‘shimcha matn
    if data == "manage_text":
        keyboard = [
            [InlineKeyboardButton("➕ Qo‘shish", callback_data="add_extra")],
            [InlineKeyboardButton("🔍 Ko‘rish", callback_data="check_extra")],
            [InlineKeyboardButton("🗑 O‘chirish", callback_data="delete_extra")]
        ]
        await query.message.reply_text("Boshqarish:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "add_extra":
        context.user_data["action"] = "add_extra"
        await query.message.reply_text("Matn yozing:")
        return

    if data == "check_extra":
        cursor.execute("SELECT code, extra_text FROM films")
        f = cursor.fetchall()
        msg = "Qo‘shimcha matnlar:\n"
        for i in f:
            msg += f"{i[0]} → {i[1]}\n"
        await query.message.reply_text(msg)
        return

    if data == "delete_extra":
        cursor.execute("UPDATE films SET extra_text=''")
        conn.commit()
        await query.message.reply_text("O‘chirildi!")
        return

    if data.startswith("update_"):
        code = data.split("_")[1]
        context.user_data["action"] = "update_code"
        context.user_data["old_code"] = code
        await query.message.reply_text("Yangi kodni yozing:")
        return

    if data.startswith("delete_"):
        code = data.split("_")[1]
        cursor.execute("DELETE FROM films WHERE code=?", (code,))
        conn.commit()
        await query.message.reply_text("Video o‘chirildi!")
        return


# ---------- OWNER VIDEO ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if update.message.video:
        context.user_data["video_file_id"] = update.message.video.file_id
        context.user_data["action"] = "set_code"
        await update.message.reply_text("Videoga kod yozing:")


# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")

    # -------- OWNER --------
    if user_id == OWNER_ID:

        if action == "set_code":
            file_id = context.user_data["video_file_id"]
            cursor.execute("INSERT OR REPLACE INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()

            keyboard = [
                [InlineKeyboardButton("✏ Kodni almashtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ O‘chirish", callback_data=f"delete_{text}")]
            ]

            await update.message.reply_video(file_id, caption=f"Kod: {text}\n{BOT_USERNAME}", reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data.clear()
            return

        if action == "search_video":
            cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (text,))
            result = cursor.fetchone()
            if not result:
                await update.message.reply_text("Topilmadi!")
            else:
                file_id, extra_text = result
                caption = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                keyboard = [
                    [InlineKeyboardButton("✏ Almashtirish", callback_data=f"update_{text}"),
                     InlineKeyboardButton("❌ O‘chirish", callback_data=f"delete_{text}")]
                ]
                await update.message.reply_video(file_id, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

            context.user_data.clear()
            return

        if action == "add_channel":
            cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            conn.commit()
            await update.message.reply_text("Qo‘shildi!")
            context.user_data.clear()
            return

        if action == "delete_channel":
            cursor.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text("O‘chirildi!")
            context.user_data.clear()
            return

        if action == "broadcast":
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            c = 0
            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                    c += 1
                except:
                    pass
            await update.message.reply_text(f"{c} ta userga yuborildi!")
            context.user_data.clear()
            return

        if action == "add_extra":
            cursor.execute("UPDATE films SET extra_text=?", (text,))
            conn.commit()
            await update.message.reply_text("Qo‘shimcha matn qo‘shildi!")
            context.user_data.clear()
            return

        if action == "update_code":
            old_code = context.user_data["old_code"]
            cursor.execute("UPDATE films SET code=? WHERE code=?", (text, old_code))
            conn.commit()
            await update.message.reply_text("Kod yangilandi!")
            context.user_data.clear()
            return

    # -------- USER FILM KO‘RISH --------
    cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (text,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("Bunday kod topilmadi!")
        return

    file_id, extra_text = result

    cursor.execute("SELECT channel FROM channels")
    channels = cursor.fetchall()

    not_subscribed = []
    for c in channels:
        try:
            st = await context.bot.get_chat_member(c[0], user_id)
            if st.status in ["left", "kicked"]:
                not_subscribed.append(c[0])
        except:
            not_subscribed.append(c[0])

    if not_subscribed:
        keyboard = [
            [InlineKeyboardButton(f"Obuna: {ch}", url=f"https://t.me/{ch[1:]}")]
            for ch in not_subscribed
        ]
        keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{text}")])

        await update.message.reply_text(
            "Avval kanallarga obuna bo‘ling:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    caption = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
    await update.message.reply_video(file_id, caption=caption)


# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()

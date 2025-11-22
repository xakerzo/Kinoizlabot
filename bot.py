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
    file_id TEXT NOT NULL
)
""")
# extra_text ustuni mavjud bo'lmasa qo'shish
try:
    cursor.execute("ALTER TABLE films ADD COLUMN extra_text TEXT DEFAULT ''")
    conn.commit()
except sqlite3.OperationalError:
    pass

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

    # Owner paneli
    if user_id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
            [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 Kanalni o‘chirish", callback_data="delete_channel")],
            [InlineKeyboardButton("📋 Kanallar ro‘yxati", callback_data="list_channels")],
            [InlineKeyboardButton("📝 Qo‘shimcha matn", callback_data="manage_text")],
            [InlineKeyboardButton("👥 Foydalanuvchilar soni", callback_data="user_count")],
            [InlineKeyboardButton("🤝 Hamkor kanallarni boshqarish", callback_data="manage_partners")]
        ]
        await update.message.reply_text("Salom Owner! Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Foydalanuvchi uchun start (inline tugmasiz)
    else:
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()

        msg = "Salom!\n\n📌 Bizning hamkorlar va kanallar:\n"
        if channels:
            for c in channels:
                msg += f"{c[0]}\n"
        else:
            msg += "Hozircha hamkor kanallar mavjud emas.\n"

        await update.message.reply_text(msg)
        await update.message.reply_text("Endi kino kodi kiriting:")

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
            msg = "Iltimos, kinoni ko‘rishdan oldin quyidagi kanallarga obuna bo‘ling:\n"
            for ch in not_subscribed:
                msg += f"{ch}\n"
            msg += "\nObuna bo‘lgach, qayta kodi kiriting."
            await query.message.reply_text(msg)
        else:
            caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
            await query.message.reply_video(file_id, caption=caption_text)
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
        await query.message.reply_text(
            "Broadcast yuborish uchun quyidagi formatlardan foydalaning:\n"
            "- Matn yuborish: faqat matn yozing\n"
            "- Rasm + caption: rasm yuboring va caption yozing\n"
            "- Video + caption: video yuboring va caption yozing"
        )
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

    elif data == "user_count":
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await query.message.reply_text(f"Botdagi foydalanuvchilar soni: {count}")
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

    # ---------- OWNER HAMKOR KANALLAR ----------
    elif data == "manage_partners":
        keyboard = [
            [InlineKeyboardButton("➕ Qo‘shish", callback_data="add_partner")],
            [InlineKeyboardButton("🔍 Tekshirish", callback_data="check_partner")],
            [InlineKeyboardButton("🗑 O‘chirish", callback_data="delete_partner")]
        ]
        await query.message.reply_text("Bizning hamkor kanallarni boshqarish:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data == "add_partner":
        context.user_data["action"] = "add_partner"
        await query.message.reply_text("Xamkor kanal nomini yozing (masalan @kanal_nomi):")
        return

    elif data == "check_partner":
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        if channels:
            msg = "Hamkor kanallar:\n" + "\n".join([c[0] for c in channels])
        else:
            msg = "Hozircha hamkor kanallar mavjud emas."
        await query.message.reply_text(msg)
        return

    elif data == "delete_partner":
        context.user_data["action"] = "delete_partner"
        await query.message.reply_text("O‘chiriladigan hamkor kanal nomini yozing:")
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
            cursor.execute("INSERT OR REPLACE INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()
            await update.message.reply_text(f"Video saqlandi! Kod: {text}")
            context.user_data.clear()
            return

        # Video kodi qidirish
        if action == "search_video":
            cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (text,))
            result = cursor.fetchone()
            if result:
                file_id, extra_text = result
                caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                await update.message.reply_video(file_id, caption=caption_text)
            else:
                await update.message.reply_text("Bunday kodga film topilmadi!")
            context.user_data.clear()
            return

        # Kanal qo‘shish
        if action == "add_channel":
            cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            conn.commit()
            await update.message.reply_text(f"Kanal qo‘shildi: {text}")
            context.user_data.clear()
            return

        # Kanal o‘chirish
        if action == "delete_channel":
            cursor.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text(f"Kanal o‘chirildi: {text}")
            context.user_data.clear()
            return

        # Broadcast
        if action == "broadcast":
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            count = 0

            # Video
            if update.message.video:
                file_id = update.message.video.file_id
                caption = text
                for u in users:
                    try:
                        await context.bot.send_video(u[0], file_id, caption=caption)
                        count += 1
                    except:
                        pass
                await update.message.reply_text(f"Video broadcast {count} foydalanuvchiga yuborildi!")
                context.user_data.clear()
                return

            # Rasm
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                caption = text
                for u in users:
                    try:
                        await context.bot.send_photo(u[0], file_id, caption=caption)
                        count += 1
                    except:
                        pass
                await update.message.reply_text(f"Rasm broadcast {count} foydalanuvchiga yuborildi!")
                context.user_data.clear()
                return

            # Matn
            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"Matn broadcast {count} foydalanuvchiga yuborildi!")
            context.user_data.clear()
            return

        # Qo‘shimcha matn barcha videolarga qo‘shish
        if action == "add_extra":
            cursor.execute("UPDATE films SET extra_text=?", (text,))
            conn.commit()
            await update.message.reply_text("Qo‘shimcha matn barcha videolarga qo‘shildi!")
            context.user_data.clear()
            return

        # Qo‘shimcha matn barcha videolardan o‘chirish
        if action == "delete_extra":
            cursor.execute("UPDATE films SET extra_text=''")
            conn.commit()
            await update.message.reply_text("Qo‘shimcha matn barcha videolardan o‘chirildi!")
            context.user_data.clear()
            return

        # Owner kodi alishtirish
        if action == "update_code":
            new_code = text
            old_code = context.user_data.get("old_code")
            cursor.execute("UPDATE films SET code=? WHERE code=?", (new_code, old_code))
            conn.commit()
            await update.message.reply_text(f"Video kodi yangilandi! Yangi kod: {new_code}")
            context.user_data.clear()
            return

        # Hamkor kanal qo‘shish
        if action == "add_partner":
            cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            conn.commit()
            await update.message.reply_text(f"Hamkor kanal qo‘shildi: {text}")
            context.user_data.clear()
            return

        # Hamkor kanal o‘chirish
        if action == "delete_partner":
            cursor.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text(f"Hamkor kanal o‘chirildi: {text}")
            context.user_data.clear()
            return

    # ---------- FOYDALANUVCHI KINO KO‘RISH ----------
    else:
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
                msg = "Iltimos, kinoni ko‘rishdan oldin quyidagi kanallarga obuna bo‘ling:\n"
                for ch in not_subscribed:
                    msg += f"{ch}\n"
                msg += "\nObuna bo‘lgach, qayta kodi kiriting."
                await update.message.reply_text(msg)
            else:
                caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                await update.message.reply_video(file_id, caption=caption_text)
                await update.message.reply_text("Agar boshqa kino ko‘rmoqchi bo‘lsangiz, yangi kodi kiriting:")
        else:
            await update.message.reply_text("Bunday kodga film topilmadi!\nIltimos, boshqa kod kiriting.")

# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_polling()

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
    pass  # ustun allaqachon mavjud bo'lsa xato bermaydi

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
# Hamkorlar jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL
)
""")
conn.commit()

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    # Hamkorlar matnini olish
    cursor.execute("SELECT text FROM partners ORDER BY id")
    partners_texts = cursor.fetchall()
    
    if partners_texts:
        partners_message = "🤝 Hamkorlarimiz:\n" + "\n".join([text[0] for text in partners_texts])
        await update.message.reply_text(partners_message)

    if user_id == OWNER_ID:
        # Foydalanuvchilar sonini hisoblash
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        keyboard = [
            [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
            [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="delete_channel")],
            [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
            [InlineKeyboardButton("📝 Qo'shimcha matn", callback_data="manage_text")],
            [InlineKeyboardButton("🤝 Hamkorlar", callback_data="manage_partners")],
            [InlineKeyboardButton(f"👥 Foydalanuvchilar: {user_count}", callback_data="user_count")]
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

    # ---------- FOYDALANUVCHI OBUNA TEKSHIRISH ----------
    if data.startswith("check_subs_"):
        code = data.split("_")[-1]
        cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (code,))
        result = cursor.fetchone()
        if not result:
            await query.message.reply_text("Bunday kodga film topilmadi!")
            return
        file_id, extra_text = result

        # Kanallarga obuna tekshirish
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
            keyboard = [[InlineKeyboardButton(f"✅ Obuna bo'lish: {ch}", url=f"https://t.me/{ch[1:]}")] for ch in not_subscribed]
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{code}")])
            await query.message.reply_text(
                "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{code}"),
                 InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{code}")]
            ]
            await query.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
        return

    # ---------- OWNER TUGMALAR ----------
    if user_id != OWNER_ID:
        return

    if data == "upload_video":
        context.user_data["action"] = "upload_video"
        await query.message.reply_text("Video yuboring:")
        return

    elif data == "search_video":
        context.user_data["action"] = "search_video"
        await query.message.reply_text("Qidiriladigan kodni yozing:")
        return

    elif data == "broadcast":
        context.user_data["action"] = "broadcast"
        await query.message.reply_text("Broadcast xabar yuboring (matn, rasm, video yoki boshqa media bilan):")
        return

    elif data == "add_channel":
        context.user_data["action"] = "add_channel"
        await query.message.reply_text("Kanal nomini yozing (masalan @kanal_nomi):")
        return

    elif data == "delete_channel":
        context.user_data["action"] = "delete_channel"
        await query.message.reply_text("O'chiriladigan kanal nomini yozing:")
        return

    elif data == "list_channels":
        cursor.execute("SELECT channel FROM channels")
        channels = cursor.fetchall()
        if channels:
            text = "Kanallar ro'yxati:\n" + "\n".join([c[0] for c in channels])
        else:
            text = "Hali kanal qo'shilmagan."
        await query.message.reply_text(text)
        return

    elif data == "user_count":
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        await query.message.reply_text(f"Botdagi jami foydalanuvchilar soni: {user_count}")
        return

    # ---------- HAMKORLAR TUGMALARI ----------
    elif data == "manage_partners":
        keyboard = [
            [InlineKeyboardButton("➕ Hamkor qo'shish", callback_data="add_partner")],
            [InlineKeyboardButton("🔍 Hamkorlarni ko'rish", callback_data="view_partners")],
            [InlineKeyboardButton("🗑 Hamkorni o'chirish", callback_data="delete_partner")]
        ]
        await query.message.reply_text(
            "Hamkorlarni boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "add_partner":
        context.user_data["action"] = "add_partner"
        await query.message.reply_text("Hamkor matnini yozing (masalan: UC servis @zakirshax):")
        return

    elif data == "view_partners":
        cursor.execute("SELECT text FROM partners ORDER BY id")
        partners = cursor.fetchall()
        if partners:
            text = "🤝 Hamkorlar ro'yxati:\n" + "\n".join([f"{i+1}. {p[0]}" for i, p in enumerate(partners)])
        else:
            text = "Hali hamkor qo'shilmagan."
        await query.message.reply_text(text)
        return

    elif data == "delete_partner":
        context.user_data["action"] = "delete_partner"
        cursor.execute("SELECT id, text FROM partners ORDER BY id")
        partners = cursor.fetchall()
        if partners:
            text = "O'chirish uchun hamkor raqamini yozing:\n" + "\n".join([f"{i+1}. {p[1]}" for i, p in enumerate(partners)])
            await query.message.reply_text(text)
        else:
            await query.message.reply_text("O'chirish uchun hamkorlar mavjud emas.")
        return

    # ---------- INLINE QO'SHIMCHA MATN TUGMALARI ----------
    elif data == "manage_text":
        keyboard = [
            [InlineKeyboardButton("➕ Qo'shish", callback_data="add_extra")],
            [InlineKeyboardButton("🔍 Tekshirish", callback_data="check_extra")],
            [InlineKeyboardButton("🗑 O'chirish", callback_data="delete_extra")]
        ]
        await query.message.reply_text(
            "Video tagidagi qo'shimcha matnni boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "add_extra":
        context.user_data["action"] = "add_extra"
        await query.message.reply_text("Matnni yozing, u barcha videolarga qo'shiladi:")
        return

    elif data == "check_extra":
        cursor.execute("SELECT code, extra_text FROM films")
        films = cursor.fetchall()
        if films:
            msg = "Videolar va qo'shimcha matn:\n"
            for f in films:
                msg += f"Kod: {f[0]}, Matn: {f[1]}\n"
            await query.message.reply_text(msg)
        else:
            await query.message.reply_text("Hali videolar yo'q.")
        return

    elif data == "delete_extra":
        context.user_data["action"] = "delete_extra"
        await query.message.reply_text("Qo'shimcha matn barcha videolardan o'chirildi!")
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
        await query.message.reply_text(f"Video {code} o'chirildi!")
        return

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if not update.message.video:
        return
    
    action = context.user_data.get("action")
    
    # Video yuklash uchun
    if action == "upload_video":
        context.user_data["video_file_id"] = update.message.video.file_id
        context.user_data["action"] = "set_code"
        await update.message.reply_text("Video qabul qilindi! Endi video uchun kodi yozing:")
        return
    
    # Broadcast uchun video qabul qilish
    if action == "broadcast":
        context.user_data["broadcast_video"] = update.message.video.file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Video qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return

# ---------- OWNER PHOTO HANDLER ----------
async def handle_owner_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    
    action = context.user_data.get("action")
    
    # Broadcast uchun rasm qabul qilish
    if action == "broadcast":
        context.user_data["broadcast_photo"] = update.message.photo[-1].file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Rasm qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return

# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")

    # ---------- OWNER ACTIONS ----------
    if user_id == OWNER_ID:
        # Video kodi qo'shish
        if action == "set_code":
            file_id = context.user_data.get("video_file_id")
            if not file_id:
                await update.message.reply_text("Xatolik! Avval video yuboring.")
                context.user_data.clear()
                return
                
            cursor.execute("INSERT OR REPLACE INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()
            
            # Qo'shimcha matnni olish
            cursor.execute("SELECT extra_text FROM films WHERE code=?", (text,))
            result = cursor.fetchone()
            extra_text = result[0] if result else ""
            
            caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{text}")]
            ]
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
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
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                     InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{text}")]
                ]
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            else:
                await update.message.reply_text("Bunday kodga film topilmadi!")
            context.user_data.clear()
            return

        # Kanal qo'shish
        if action == "add_channel":
            cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            conn.commit()
            await update.message.reply_text(f"Kanal qo'shildi: {text}")
            context.user_data.clear()
            return

        # Kanal o'chirish
        if action == "delete_channel":
            cursor.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text(f"Kanal o'chirildi: {text}")
            context.user_data.clear()
            return

        # Broadcast tasdiqlash
        if action == "confirm_broadcast":
            if text.upper() == "HA":
                cursor.execute("SELECT user_id FROM users")
                users = cursor.fetchall()
                count = 0
                failed = 0
                
                broadcast_photo = context.user_data.get("broadcast_photo")
                broadcast_video = context.user_data.get("broadcast_video")
                broadcast_caption = context.user_data.get("broadcast_caption", "")
                
                for u in users:
                    try:
                        if broadcast_photo:
                            await context.bot.send_photo(u[0], broadcast_photo, caption=broadcast_caption)
                        elif broadcast_video:
                            await context.bot.send_video(u[0], broadcast_video, caption=broadcast_caption)
                        else:
                            # Agar media bo'lmasa, faqat matn yuboriladi
                            await context.bot.send_message(u[0], broadcast_caption)
                        count += 1
                    except Exception as e:
                        print(f"Xatolik: {e}")
                        failed += 1
                
                await update.message.reply_text(f"✅ Xabar {count} foydalanuvchiga yuborildi! ❌ {failed} ta yuborilmadi.")
            else:
                await update.message.reply_text("Broadcast bekor qilindi.")
            
            context.user_data.clear()
            return

        # Oddiy broadcast (faqat matn)
        if action == "broadcast" and not context.user_data.get("broadcast_photo") and not context.user_data.get("broadcast_video"):
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            count = 0
            failed = 0
            for u in users:
                try:
                    await context.bot.send_message(u[0], text)
                    count += 1
                except:
                    failed += 1
            await update.message.reply_text(f"✅ Xabar {count} foydalanuvchiga yuborildi! ❌ {failed} ta yuborilmadi.")
            context.user_data.clear()
            return

        # Qo'shimcha matn barcha videolarga qo'shish
        if action == "add_extra":
            cursor.execute("UPDATE films SET extra_text=?", (text,))
            conn.commit()
            await update.message.reply_text("Qo'shimcha matn barcha videolarga qo'shildi!")
            context.user_data.clear()
            return

        # Qo'shimcha matn barcha videolardan o'chirish
        if action == "delete_extra":
            cursor.execute("UPDATE films SET extra_text=''")
            conn.commit()
            await update.message.reply_text("Qo'shimcha matn barcha videolardan o'chirildi!")
            context.user_data.clear()
            return

        # Owner kodi alishtirish
        if action == "update_code":
            new_code = text
            old_code = context.user_data.get("old_code")
            cursor.execute("UPDATE films SET code=? WHERE code=?", (new_code, old_code))
            conn.commit()
            cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (new_code,))
            result = cursor.fetchone()
            if result:
                file_id, extra_text = result
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{new_code}"),
                     InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{new_code}")]
                ]
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=f"Kod: {new_code}\n{extra_text}\n{BOT_USERNAME}")
            await update.message.reply_text(f"Video kodi yangilandi! Yangi kod: {new_code}")
            context.user_data.clear()
            return

        # Hamkor qo'shish
        if action == "add_partner":
            cursor.execute("INSERT INTO partners (text) VALUES (?)", (text,))
            conn.commit()
            await update.message.reply_text(f"Hamkor qo'shildi: {text}")
            context.user_data.clear()
            return

        # Hamkor o'chirish
        if action == "delete_partner":
            try:
                partner_num = int(text)
                cursor.execute("SELECT id FROM partners ORDER BY id")
                partners = cursor.fetchall()
                if 1 <= partner_num <= len(partners):
                    partner_id = partners[partner_num-1][0]
                    cursor.execute("DELETE FROM partners WHERE id=?", (partner_id,))
                    conn.commit()
                    await update.message.reply_text(f"Hamkor #{partner_num} o'chirildi!")
                else:
                    await update.message.reply_text("Noto'g'ri raqam!")
            except ValueError:
                await update.message.reply_text("Iltimos, raqam kiriting!")
            context.user_data.clear()
            return

    # ---------- FOYDALANUVCHI KINO KO'RISH ----------
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
            keyboard = [[InlineKeyboardButton(f"✅ Obuna bo'lish: {ch}", url=f"https://t.me/{ch[1:]}")] for ch in not_subscribed]
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{text}")])
            await update.message.reply_text(
                "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{text}")]
            ] if user_id == OWNER_ID else None
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, caption=caption_text)
    else:
        await update.message.reply_text("Bunday kodga film topilmadi!")

# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.PHOTO, handle_owner_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_polling()

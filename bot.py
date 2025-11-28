# bot.py - To'liq PostgreSQL bilan moslangan kod
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timedelta

# ---------- TOKEN VA OWNER ----------
OWNER_ID = 1373647
BOT_TOKEN = os.environ.get('BOT_TOKEN')
BOT_USERNAME = "@kinoni_izlabot"

# ---------- DATABASE ----------
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL ulash
    result = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require'
    )
    cursor = conn.cursor()
    
    # PostgreSQL uchun jadvallar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS films (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            extra_text TEXT DEFAULT ''
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel TEXT PRIMARY KEY
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partners (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_users (
            user_id BIGINT PRIMARY KEY,
            expiry_date TIMESTAMP,
            approved_by BIGINT,
            approved_date TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bypass_requests (
            user_id BIGINT PRIMARY KEY,
            request_text TEXT,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ad_texts (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL
        )
    """)
    
else:
    # Lokal SQLite uchun (developerni tekshirish)
    import sqlite3
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_users (
            user_id INTEGER PRIMARY KEY,
            expiry_date TIMESTAMP,
            approved_by INTEGER,
            approved_date TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bypass_requests (
            user_id INTEGER PRIMARY KEY,
            request_text TEXT,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ad_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )
    """)

conn.commit()

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Database ga user qo'shish
    if DATABASE_URL:
        cursor.execute("""
            INSERT INTO users (user_id) 
            VALUES (%s) 
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id,))
    else:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    # Premium tekshirish
    cursor.execute("SELECT expiry_date FROM premium_users WHERE user_id = %s" if DATABASE_URL else "SELECT expiry_date FROM premium_users WHERE user_id=?", (user_id,))
    premium_result = cursor.fetchone()
    is_premium = premium_result and datetime.fromisoformat(premium_result[0]) > datetime.now()

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
            [InlineKeyboardButton("🎫 Reklama sozlamalari", callback_data="ad_settings")],
            [InlineKeyboardButton("👤 Premium boshqarish", callback_data="premium_management")],
            [InlineKeyboardButton(f"👥 Foydalanuvchilar: {user_count}", callback_data="user_count")]
        ]
        await update.message.reply_text("Salom Owner! Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        if is_premium:
            await update.message.reply_text("🎉 Siz premium foydalanuvchisiz! Kanallarga obuna bo'lish shart emas.\n\nKino kodi kiriting:")
        else:
            await update.message.reply_text("Salom! Kino kodi kiriting:")

# ---------- CALLBACK HANDLER ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    try:
        await query.answer()
    except Exception as e:
        print(f"Callback query error: {e}")
        return

    # ---------- REKLAMA BYPASS TUGMASI ----------
    if data == "bypass_ads":
        cursor.execute("SELECT text FROM ad_texts ORDER BY id DESC LIMIT 1")
        ad_result = cursor.fetchone()
        
        if ad_result:
            ad_text = ad_result[0]
        else:
            ad_text = "Iltimos, botdan foydalanish uchun quyidagi kanallarga obuna bo'ling yoki admin bilan bog'laning."
        
        keyboard = [
            [InlineKeyboardButton("📨 Chekni yuborish", callback_data="send_receipt")]
        ]
        await query.message.reply_text(
            f"{ad_text}\n\nAgar sizda reklama/obuna bypass qilish uchun chek bo'lsa, uni yuborishingiz mumkin:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "send_receipt":
        context.user_data.clear()
        context.user_data["action"] = "waiting_receipt"
        await query.message.reply_text(
            "Iltimos, chek yoki tasdiqlovchi hujjatning skrinshotini yuboring. "
            "Admin tekshirgach sizga premium beriladi va siz kanallarga obuna bo'lishsiz botdan foydalana olasiz."
        )
        return

    # ---------- FOYDALANUVCHI OBUNA TEKSHIRISH ----------
    if data.startswith("check_subs_"):
        code = data.split("_")[-1]
        
        # Premium tekshirish
        cursor.execute("SELECT expiry_date FROM premium_users WHERE user_id = %s" if DATABASE_URL else "SELECT expiry_date FROM premium_users WHERE user_id=?", (user_id,))
        premium_result = cursor.fetchone()
        is_premium = premium_result and datetime.fromisoformat(premium_result[0]) > datetime.now()
        
        if is_premium:
            cursor.execute("SELECT file_id, extra_text FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (code,))
            result = cursor.fetchone()
            if result:
                file_id, extra_text = result
                caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
                await query.message.reply_video(file_id, caption=caption_text)
            return

        # Oddiy foydalanuvchi uchun obuna tekshirish
        cursor.execute("SELECT file_id, extra_text FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (code,))
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
            keyboard = []
            for ch in not_subscribed:
                keyboard.append([InlineKeyboardButton(f"✅ Obuna bo'lish: {ch}", url=f"https://t.me/{ch[1:]}")])
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{code}")])
            keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
            await query.message.reply_text(
                "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
            await query.message.reply_video(file_id, caption=caption_text)
        return

    # ---------- OWNER TUGMALARI ----------
    if user_id != OWNER_ID:
        return

    # Owner tugmalari (qisqartirilgan)
    if data == "upload_video":
        context.user_data.clear()
        context.user_data["action"] = "upload_video"
        await query.message.reply_text("Video yuboring:")
        return

    elif data == "search_video":
        context.user_data.clear()
        context.user_data["action"] = "search_video"
        await query.message.reply_text("Qidiriladigan kodni yozing:")
        return

    # ... (qolgan owner tugmalari o'xshash)

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if not update.message.video:
        return
    
    action = context.user_data.get("action")
    
    if action == "upload_video":
        context.user_data["video_file_id"] = update.message.video.file_id
        context.user_data["action"] = "set_code"
        await update.message.reply_text("Video qabul qilindi! Endi video uchun kodi yozing:")
        return
    
    if not action or action == "upload_video":
        context.user_data.clear()
        context.user_data["video_file_id"] = update.message.video.file_id
        context.user_data["action"] = "set_code"
        await update.message.reply_text("Video qabul qilindi! Endi video uchun kodi yozing:")
        return
    
    if action == "broadcast":
        context.user_data["broadcast_video"] = update.message.video.file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Video qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
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
            
            # Kod bandligini tekshirish
            cursor.execute("SELECT * FROM films WHERE code = %s" if DATABASE_URL else "SELECT * FROM films WHERE code=?", (text,))
            if cursor.fetchone():
                await update.message.reply_text(f"⚠️ Bu kod band! Boshqa kod kiriting:")
                return
                
            if DATABASE_URL:
                cursor.execute("INSERT INTO films (code, file_id) VALUES (%s, %s) ON CONFLICT (code) DO UPDATE SET file_id = EXCLUDED.file_id", (text, file_id))
            else:
                cursor.execute("INSERT OR REPLACE INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            conn.commit()
            
            cursor.execute("SELECT extra_text FROM films WHERE code = %s" if DATABASE_URL else "SELECT extra_text FROM films WHERE code=?", (text,))
            result = cursor.fetchone()
            extra_text = result[0] if result else ""
            
            caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{text}"),
                 InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{text}")]
            ]
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            await update.message.reply_text(f"✅ Video saqlandi! Kod: {text}")
            
            context.user_data["video_file_id"] = None
            context.user_data["action"] = "upload_video"
            return

        # ... (qolgan owner actions)

    # ---------- FOYDALANUVCHI KINO KO'RISH ----------
    cursor.execute("SELECT file_id, extra_text FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (text,))
    result = cursor.fetchone()
    if result:
        file_id, extra_text = result
        
        cursor.execute("SELECT expiry_date FROM premium_users WHERE user_id = %s" if DATABASE_URL else "SELECT expiry_date FROM premium_users WHERE user_id=?", (user_id,))
        premium_result = cursor.fetchone()
        is_premium = premium_result and datetime.fromisoformat(premium_result[0]) > datetime.now()
        
        if is_premium:
            caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            await update.message.reply_video(file_id, caption=caption_text)
        else:
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
                keyboard = []
                for ch in not_subscribed:
                    keyboard.append([InlineKeyboardButton(f"✅ Obuna bo'lish: {ch}", url=f"https://t.me/{ch[1:]}")])
                keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{text}")])
                keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
                await update.message.reply_text(
                    "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                await update.message.reply_video(file_id, caption=caption_text)
    else:
        await update.message.reply_text("Bunday kodga film topilmadi!")

# ---------- QOLGAN HANDLERLAR ----------
async def handle_owner_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    
    action = context.user_data.get("action")
    
    if action == "broadcast":
        context.user_data["broadcast_photo"] = update.message.photo[-1].file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Rasm qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id == OWNER_ID:
        await handle_owner_photo(update, context)
        return
    
    action = context.user_data.get("action")
    if action == "waiting_receipt":
        photo_file = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO bypass_requests (user_id, request_text, status) 
                VALUES (%s, %s, 'pending')
                ON CONFLICT (user_id) DO UPDATE SET 
                request_text = EXCLUDED.request_text,
                request_date = CURRENT_TIMESTAMP,
                status = 'pending'
            """, (user_id, caption))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO bypass_requests (user_id, request_text, status) 
                VALUES (?, ?, 'pending')
            """, (user_id, caption))
        conn.commit()
        
        try:
            await context.bot.send_photo(
                OWNER_ID, 
                photo_file, 
                caption=f"📨 Yangi chek so'rovi!\nUser ID: {user_id}\nIzoh: {caption}\n\nPremium berish uchun /premium {user_id} 30"
            )
        except Exception as e:
            print(f"Xatolik ownerga xabar yuborishda: {e}")
        
        await update.message.reply_text(
            "✅ Chek qabul qilindi! Admin tekshiradi va sizga premium beriladi. "
            "Tasdiqlash uchun biroz kuting."
        )
        context.user_data.clear()

# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == '__main__':
    print("Bot ishga tushdi...")
    app.run_polling()

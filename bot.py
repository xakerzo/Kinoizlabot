from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import urllib.parse
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timedelta
import hashlib

# ---------- TOKEN VA OWNER ----------
OWNER_ID = 1373647
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8505113284:AAFu0vhU6j7d4tsaY5Rsn1qga57THZt3pEo")
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
    
    # YANGI JADVALLAR
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_captions (
            id SERIAL PRIMARY KEY,
            caption_text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_buttons (
            id SERIAL PRIMARY KEY,
            button_text TEXT NOT NULL,
            button_url TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_links (
            id SERIAL PRIMARY KEY,
            link_text TEXT NOT NULL,
            link_url TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id BIGINT PRIMARY KEY,
            added_by BIGINT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
else:
    # Lokal SQLite uchun
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
    
    # YANGI JADVALLAR
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_captions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caption_text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button_text TEXT NOT NULL,
            button_url TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_text TEXT NOT NULL,
            link_url TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

conn.commit()

# ---------- DATABASE FUNCTIONS ----------
def execute_query(query, params=None):
    """Barcha SQL so'rovlarni bajarish"""
    if DATABASE_URL:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
    else:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
    conn.commit()

def fetch_one(query, params=None):
    """Bitta natija olish"""
    if DATABASE_URL and params:
        cursor.execute(query, params)
    elif DATABASE_URL:
        cursor.execute(query)
    elif params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    return cursor.fetchone()

def fetch_all(query, params=None):
    """Barcha natijalarni olish"""
    if DATABASE_URL and params:
        cursor.execute(query, params)
    elif DATABASE_URL:
        cursor.execute(query)
    elif params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    return cursor.fetchall()

def is_premium_user(user_id):
    """Premium foydalanuvchini tekshirish"""
    result = fetch_one("SELECT expiry_date FROM premium_users WHERE user_id=%s" if DATABASE_URL else "SELECT expiry_date FROM premium_users WHERE user_id=?", (user_id,))
    
    if not result:
        return False
    
    expiry_date = result[0]
    
    # PostgreSQL dan datetime obyekt qaytadi, SQLite dan string
    if isinstance(expiry_date, datetime):
        # PostgreSQL - to'g'ridan-to'g'ri datetime
        return expiry_date > datetime.now()
    else:
        # SQLite - string, convert qilish kerak
        return datetime.fromisoformat(expiry_date) > datetime.now()

def is_admin(user_id):
    """Admin foydalanuvchini tekshirish"""
    if user_id == OWNER_ID:
        return True
    result = fetch_one("SELECT user_id FROM admins WHERE user_id=%s" if DATABASE_URL else "SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    return result is not None

# ---------- CALLBACK DATA YORDAMCHI FUNKSIYALARI ----------
def create_safe_callback_data(code):
    """Uzun kodlar (Instagram linklari) uchun xavfsiz callback data yaratish"""
    if len(code) > 50:  # Agar kod juda uzun bo'lsa
        # Hash yaratish
        hash_object = hashlib.md5(code.encode())
        short_code = hash_object.hexdigest()[:10]
    else:
        short_code = code
    return short_code

def get_original_code_from_callback(short_code):
    """Qisqartirilgan kod orqali asl kodni topish"""
    # Bazadan qidirish
    films = fetch_all("SELECT code FROM films")
    for film in films:
        original_code = film[0]
        if create_safe_callback_data(original_code) == short_code:
            return original_code
    return short_code  # Topilmasa, short_code ni qaytarish

# ---------- YANGI FUNKSIYALAR: TUGMA VA XABARLARNI YUBORISH ----------
async def send_video_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Video tugmalarini yuborish"""
    try:
        button_result = fetch_one("SELECT button_text, button_url FROM video_buttons ORDER BY id DESC LIMIT 1")
        
        if button_result:
            button_text, button_url = button_result
            
            # ✅ URL ni tekshirish va to'g'rilash
            if button_url.startswith('@'):
                # Agar @ bilan boshlansa, Telegram linkiga aylantirish
                button_url = f"https://t.me/{button_url[1:]}"
            elif not button_url.startswith(('http://', 'https://')):
                # Agar http(s) bo'lmasa, https qo'shamiz
                button_url = f"https://{button_url}"
            
            keyboard = [
                [InlineKeyboardButton(button_text, url=button_url)],
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await update.message.reply_text(
                "Quyidagi tugmalardan foydalaning:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Agar tugma bo'lmasa, faqat ulashish tugmasini chiqaramiz
            keyboard = [
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await update.message.reply_text(
                "Quyidagi tugmalardan foydalaning:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        print(f"Tugma yuborishda xatolik: {e}")

async def send_video_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Video xabarini yuborish"""
    try:
        caption_result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        
        if caption_result:
            await update.message.reply_text(caption_result[0])
    except Exception as e:
        print(f"Xabar yuborishda xatolik: {e}")

# ---------- CALLBACK UCHUN YANGI FUNKSIYALAR ----------
async def send_callback_buttons(query, context: ContextTypes.DEFAULT_TYPE):
    """Callback uchun video tugmalarini yuborish"""
    try:
        button_result = fetch_one("SELECT button_text, button_url FROM video_buttons ORDER BY id DESC LIMIT 1")
        
        if button_result:
            button_text, button_url = button_result
            
            # ✅ URL ni tekshirish va to'g'rilash
            if button_url.startswith('@'):
                # Agar @ bilan boshlansa, Telegram linkiga aylantirish
                button_url = f"https://t.me/{button_url[1:]}"
            elif not button_url.startswith(('http://', 'https://')):
                # Agar http(s) bo'lmasa, https qo'shamiz
                button_url = f"https://{button_url}"
            
            keyboard = [
                [InlineKeyboardButton(button_text, url=button_url)],
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await query.message.reply_text(
                "Quyidagi tugmalardan foydalaning:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Agar tugma bo'lmasa, faqat ulashish tugmasini chiqaramiz
            keyboard = [
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await query.message.reply_text(
                "Quyidagi tugmalardan foydalaning:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        print(f"Callback tugma yuborishda xatolik: {e}")

async def send_callback_caption(query, context: ContextTypes.DEFAULT_TYPE):
    """Callback uchun video xabarini yuborish"""
    try:
        caption_result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        
        if caption_result:
            await query.message.reply_text(caption_result[0])
    except Exception as e:
        print(f"Callback xabar yuborishda xatolik: {e}")

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if DATABASE_URL:
        execute_query("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    else:
        execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    is_premium = is_premium_user(user_id)

    # Hamkorlar matnini olish
    partners_texts = fetch_all("SELECT text FROM partners ORDER BY id")
    
    if partners_texts:
        partners_message = "🤝 Hamkorlarimiz:\n" + "\n".join([text[0] for text in partners_texts])
        await update.message.reply_text(partners_message)

    if user_id == OWNER_ID or is_admin(user_id):
        # Foydalanuvchilar sonini hisoblash
        user_count = fetch_one("SELECT COUNT(*) FROM users")[0]
        
        keyboard = [
            [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
            [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
        ]
        
        # Faqat owner uchun admin funksiyalari
        if user_id == OWNER_ID:
            keyboard.extend([
                [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
                [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
                [InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="delete_channel")],
                [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
                [InlineKeyboardButton("📝 Qo'shimcha matn", callback_data="manage_text")],
                [InlineKeyboardButton("🤝 Hamkorlar", callback_data="manage_partners")],
                [InlineKeyboardButton("🎫 Reklama sozlamalari", callback_data="ad_settings")],
                [InlineKeyboardButton("👤 Premium boshqarish", callback_data="premium_management")],
                [InlineKeyboardButton("👥 Admin boshqarish", callback_data="admin_management")],
                [InlineKeyboardButton("📝 Video ostidagi xabar", callback_data="video_caption_manage")],
                [InlineKeyboardButton("🔘 Video ostidagi tugma", callback_data="video_button_manage")],
                [InlineKeyboardButton("🔗 Majburiy kanal linki", callback_data="channel_link_manage")],
            ])
        
        keyboard.append([InlineKeyboardButton(f"👥 Foydalanuvchilar: {user_count}", callback_data="user_count")])
        
        if user_id == OWNER_ID:
            await update.message.reply_text("Salom Owner! Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("Salom Admin! Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        if is_premium:
            await update.message.reply_text("🎉 Siz premium foydalanuvchisiz! Kanallarga obuna bo'lish shart emas.\n\nKino kodi yoki Instagram linkini kiriting:")
        else:
            await update.message.reply_text("Salom! Kino kodi yoki Instagram linkini kiriting:")

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
        ad_result = fetch_one("SELECT text FROM ad_texts ORDER BY id DESC LIMIT 1")
        
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
        short_code = data.replace("check_subs_", "")
        code = get_original_code_from_callback(short_code)
        
        # Premium tekshirish
        is_premium = is_premium_user(user_id)
        
        if is_premium:
            result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (code,))
            if result:
                file_id, extra_text = result
                # Agar link bo'lsa, caption ni boshqacha ko'rsatish
                if code.startswith('http'):
                    caption_text = f"Link: {code}\n{extra_text}\n{BOT_USERNAME}"
                else:
                    caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
                await query.message.reply_video(file_id, caption=caption_text)
                
                # ✅ HAR DOIM TUGMALAR CHIQSIN
                await send_callback_buttons(query, context)
                
                # ✅ HAR DOIM XABAR CHIQSIN
                await send_callback_caption(query, context)
            return

        # Oddiy foydalanuvchi uchun obuna tekshirish
        result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (code,))
        if not result:
            await query.message.reply_text("Bunday kod/linkka film topilmadi!")
            return
        file_id, extra_text = result

        # Kanallarga obuna tekshirish
        channels = fetch_all("SELECT channel FROM channels")
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
            
            # YANGI: Kanal linkini qo'shish
            link_result = fetch_one("SELECT link_text, link_url FROM channel_links ORDER BY id DESC LIMIT 1")
            if link_result:
                link_text, link_url = link_result
                keyboard.append([InlineKeyboardButton(link_text, url=link_url)])
            
            safe_code = create_safe_callback_data(code)
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{safe_code}")])
            keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
            
            await query.message.reply_text(
                "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Agar link bo'lsa, caption ni boshqacha ko'rsatish
            if code.startswith('http'):
                caption_text = f"Link: {code}\n{extra_text}\n{BOT_USERNAME}"
            else:
                caption_text = f"Kod: {code}\n{extra_text}\n{BOT_USERNAME}"
            await query.message.reply_video(file_id, caption=caption_text)
            
            # ✅ HAR DOIM TUGMALAR CHIQSIN
            await send_callback_buttons(query, context)
            
            # ✅ HAR DOIM XABAR CHIQSIN
            await send_callback_caption(query, context)
        return

    # ---------- OWNER TUGMALARI ----------
    if user_id != OWNER_ID and not is_admin(user_id):
        return

    if data == "upload_video":
        context.user_data.clear()
        context.user_data["action"] = "upload_video"
        await query.message.reply_text("Video yuboring:")
        return

    elif data == "search_video":
        context.user_data.clear()
        context.user_data["action"] = "search_video"
        await query.message.reply_text("Qidiriladigan kod yoki linkni yozing:")
        return

    elif data == "broadcast":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "broadcast"
        await query.message.reply_text("Broadcast xabar yuboring (matn, rasm, video yoki boshqa media bilan):")
        return

    elif data == "add_channel":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "add_channel"
        await query.message.reply_text("Kanal nomini yozing (masalan @kanal_nomi):")
        return

    elif data == "delete_channel":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "delete_channel"
        await query.message.reply_text("O'chiriladigan kanal nomini yozing:")
        return

    elif data == "list_channels":
        channels = fetch_all("SELECT channel FROM channels")
        if channels:
            text = "Kanallar ro'yxati:\n" + "\n".join([c[0] for c in channels])
        else:
            text = "Hali kanal qo'shilmagan."
        await query.message.reply_text(text)
        return

    elif data == "user_count":
        user_count = fetch_one("SELECT COUNT(*) FROM users")[0]
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
        context.user_data.clear()
        context.user_data["action"] = "add_partner"
        await query.message.reply_text("Hamkor matnini yozing (masalan: UC servis @zakirshax):")
        return

    elif data == "view_partners":
        partners = fetch_all("SELECT text FROM partners ORDER BY id")
        if partners:
            text = "🤝 Hamkorlar ro'yxati:\n" + "\n".join([f"{i+1}. {p[0]}" for i, p in enumerate(partners)])
        else:
            text = "Hali hamkor qo'shilmagan."
        await query.message.reply_text(text)
        return

    elif data == "delete_partner":
        context.user_data.clear()
        context.user_data["action"] = "delete_partner"
        partners = fetch_all("SELECT id, text FROM partners ORDER BY id")
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
        context.user_data.clear()
        context.user_data["action"] = "add_extra"
        await query.message.reply_text("Matnni yozing, u barcha videolarga qo'shiladi:")
        return

    elif data == "check_extra":
        films = fetch_all("SELECT code, extra_text FROM films")
        if films:
            msg = "Videolar va qo'shimcha matn:\n"
            for f in films:
                msg += f"Kod: {f[0]}, Matn: {f[1]}\n"
            await query.message.reply_text(msg)
        else:
            await query.message.reply_text("Hali videolar yo'q.")
        return

    elif data == "delete_extra":
        execute_query("UPDATE films SET extra_text=%s" if DATABASE_URL else "UPDATE films SET extra_text=?", ('',))
        await query.message.reply_text("Qo'shimcha matn barcha videolardan o'chirildi!")
        return

    elif data.startswith("update_"):
        context.user_data.clear()
        old_short_code = data.split("_")[1]
        old_code = get_original_code_from_callback(old_short_code)
        context.user_data["action"] = "update_code"
        context.user_data["old_code"] = old_code
        await query.message.reply_text(f"Yangi kodni yozing (eski kod: {old_code}):")
        return

    elif data.startswith("delete_"):
        short_code = data.split("_")[1]
        code = get_original_code_from_callback(short_code)
        execute_query("DELETE FROM films WHERE code=%s" if DATABASE_URL else "DELETE FROM films WHERE code=?", (code,))
        await query.message.reply_text(f"Video {code} o'chirildi!")
        return

    # ---------- YANGI OWNER TUGMALARI ----------
    elif data == "ad_settings":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        keyboard = [
            [InlineKeyboardButton("✏️ Reklama matnini o'zgartirish", callback_data="edit_ad_text")],
            [InlineKeyboardButton("🔍 Joriy reklama matni", callback_data="view_ad_text")],
            [InlineKeyboardButton("📨 Kelgan so'rovlar", callback_data="view_requests")]
        ]
        await query.message.reply_text(
            "Reklama sozlamalari:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "edit_ad_text":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "edit_ad_text"
        await query.message.reply_text("Yangi reklama matnini kiriting:")
        return

    elif data == "view_ad_text":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        ad_result = fetch_one("SELECT text FROM ad_texts ORDER BY id DESC LIMIT 1")
        if ad_result:
            await query.message.reply_text(f"Joriy reklama matni:\n\n{ad_result[0]}")
        else:
            await query.message.reply_text("Hali reklama matni qo'shilmagan.")
        return

    elif data == "view_requests":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        requests = fetch_all("""
            SELECT br.user_id, br.request_text, br.request_date, u.user_id 
            FROM bypass_requests br 
            LEFT JOIN users u ON br.user_id = u.user_id 
            WHERE br.status = 'pending'
        """)
        
        if not requests:
            await query.message.reply_text("Hozircha yangi so'rovlar yo'q.")
            return
        
        text = "📨 Yangi so'rovlar:\n\n"
        for i, req in enumerate(requests, 1):
            user_id, req_text, req_date, exists = req
            text += f"{i}. User ID: {user_id}\nSana: {req_date}\n"
            if req_text:
                text += f"Matn: {req_text}\n"
            text += "\n"
        
        keyboard = [[InlineKeyboardButton("📋 So'rovlarni ko'rish", callback_data="manage_requests")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data == "manage_requests":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "manage_requests"
        requests = fetch_all("SELECT user_id FROM bypass_requests WHERE status = 'pending'")
        
        if not requests:
            await query.message.reply_text("Hozircha yangi so'rovlar yo'q.")
            return
        
        text = "Premium berish uchun user ID ni kiriting:\n\n"
        for i, req in enumerate(requests, 1):
            text += f"{i}. User ID: {req[0]}\n"
        
        await query.message.reply_text(text)
        return

    elif data == "premium_management":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        keyboard = [
            [InlineKeyboardButton("👤 Userga premium berish", callback_data="give_premium")],
            [InlineKeyboardButton("📋 Premium foydalanuvchilar", callback_data="list_premium")],
            [InlineKeyboardButton("🗑 Premiumni olib tashlash", callback_data="remove_premium")]
        ]
        await query.message.reply_text(
            "Premium boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "give_premium":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "give_premium_user"
        await query.message.reply_text("Premium beriladigan user ID ni kiriting:")
        return

    elif data == "list_premium":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        premium_users = fetch_all("SELECT pu.user_id, pu.expiry_date FROM premium_users pu WHERE pu.expiry_date > CURRENT_TIMESTAMP")
        
        if not premium_users:
            await query.message.reply_text("Hozircha premium foydalanuvchilar yo'q.")
            return
        
        text = "🎫 Premium foydalanuvchilar:\n\n"
        for i, user in enumerate(premium_users, 1):
            user_id, expiry_date = user
            # PostgreSQL dan datetime obyekt qaytadi
            if isinstance(expiry_date, datetime):
                days_left = (expiry_date - datetime.now()).days
                expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M')
            else:
                # SQLite uchun
                expiry_dt = datetime.fromisoformat(expiry_date)
                days_left = (expiry_dt - datetime.now()).days
                expiry_str = expiry_date
            
            text += f"{i}. User ID: {user_id}\nMuddati: {expiry_str}\nQolgan kun: {days_left}\n\n"
        
        await query.message.reply_text(text)
        return

    elif data == "remove_premium":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        context.user_data.clear()
        context.user_data["action"] = "remove_premium_user"
        await query.message.reply_text("Premium olib tashlanadigan user ID ni kiriting:")
        return

    # ---------- YANGI ADMIN BOSHQARISH TUGMALARI ----------
    elif data == "admin_management":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        keyboard = [
            [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")],
            [InlineKeyboardButton("🔍 Adminlar ro'yxati", callback_data="list_admins")],
            [InlineKeyboardButton("🗑 Adminni o'chirish", callback_data="remove_admin")]
        ]
        await query.message.reply_text(
            "Adminlarni boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "add_admin":
        if user_id != OWNER_ID:
            return
        context.user_data.clear()
        context.user_data["action"] = "add_admin"
        await query.message.reply_text("Admin qo'shiladigan user ID ni kiriting:")
        return

    elif data == "list_admins":
        if user_id != OWNER_ID:
            return
        admins = fetch_all("SELECT user_id, added_date FROM admins ORDER BY added_date")
        text = "👥 Adminlar ro'yxati:\n\n"
        text += f"1. User ID: {OWNER_ID} (Owner)\n"
        for i, admin in enumerate(admins, 2):
            admin_id, added_date = admin
            text += f"{i}. User ID: {admin_id}\n   Qo'shilgan: {added_date}\n"
        await query.message.reply_text(text)
        return

    elif data == "remove_admin":
        if user_id != OWNER_ID:
            return
        context.user_data.clear()
        context.user_data["action"] = "remove_admin"
        await query.message.reply_text("O'chiriladigan admin ID ni kiriting:")
        return

    # ---------- YANGI VIDEO CAPTION TUGMALARI ----------
    elif data == "video_caption_manage":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        keyboard = [
            [InlineKeyboardButton("➕ Xabar qo'shish", callback_data="add_video_caption")],
            [InlineKeyboardButton("🔍 Xabarni ko'rish", callback_data="view_video_caption")],
            [InlineKeyboardButton("🗑 Xabarni o'chirish", callback_data="delete_video_caption")]
        ]
        await query.message.reply_text(
            "Video ostidagi xabarni boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "add_video_caption":
        if user_id != OWNER_ID:
            return
        context.user_data.clear()
        context.user_data["action"] = "add_video_caption"
        await query.message.reply_text("Video dan keyin chiqadigan xabarni yozing:")
        return

    elif data == "view_video_caption":
        if user_id != OWNER_ID:
            return
        result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        if result:
            await query.message.reply_text(f"Joriy video xabari:\n\n{result[0]}")
        else:
            await query.message.reply_text("Hali video xabari qo'shilmagan.")
        return

    elif data == "delete_video_caption":
        if user_id != OWNER_ID:
            return
        execute_query("DELETE FROM video_captions")
        await query.message.reply_text("✅ Video xabari o'chirildi!")
        return

    # ---------- YANGI VIDEO BUTTON TUGMALARI ----------
    elif data == "video_button_manage":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        keyboard = [
            [InlineKeyboardButton("➕ Tugma qo'shish", callback_data="add_video_button")],
            [InlineKeyboardButton("🔍 Tugmani ko'rish", callback_data="view_video_button")],
            [InlineKeyboardButton("🗑 Tugmani o'chirish", callback_data="delete_video_button")]
        ]
        await query.message.reply_text(
            "Video ostidagi tugmani boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "add_video_button":
        if user_id != OWNER_ID:
            return
        context.user_data.clear()
        context.user_data["action"] = "add_video_button_text"
        await query.message.reply_text("Tugma matnini yozing (masalan: 📺 Bizning kanal):")
        return

    elif data == "view_video_button":
        if user_id != OWNER_ID:
            return
        result = fetch_one("SELECT button_text, button_url FROM video_buttons ORDER BY id DESC LIMIT 1")
        if result:
            button_text, button_url = result
            await query.message.reply_text(f"Joriy video tugmasi:\nMatn: {button_text}\nLink: {button_url}")
        else:
            await query.message.reply_text("Hali video tugmasi qo'shilmagan.")
        return

    elif data == "delete_video_button":
        if user_id != OWNER_ID:
            return
        execute_query("DELETE FROM video_buttons")
        await query.message.reply_text("✅ Video tugmasi o'chirildi!")
        return

    # ---------- YANGI CHANNEL LINK TUGMALARI ----------
    elif data == "channel_link_manage":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat owner uchun!")
            return
        keyboard = [
            [InlineKeyboardButton("➕ Link qo'shish", callback_data="add_channel_link")],
            [InlineKeyboardButton("🔍 Linkni ko'rish", callback_data="view_channel_link")],
            [InlineKeyboardButton("🗑 Linkni o'chirish", callback_data="delete_channel_link")]
        ]
        await query.message.reply_text(
            "Majburiy kanal linkini boshqarish:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data == "add_channel_link":
        if user_id != OWNER_ID:
            return
        context.user_data.clear()
        context.user_data["action"] = "add_channel_link_text"
        await query.message.reply_text("Link tugmasi matnini yozing (masalan: 🔗 Bizning sayt):")
        return

    elif data == "view_channel_link":
        if user_id != OWNER_ID:
            return
        result = fetch_one("SELECT link_text, link_url FROM channel_links ORDER BY id DESC LIMIT 1")
        if result:
            link_text, link_url = result
            await query.message.reply_text(f"Joriy kanal linki:\nMatn: {link_text}\nLink: {link_url}")
        else:
            await query.message.reply_text("Hali kanal linki qo'shilmagan.")
        return

    elif data == "delete_channel_link":
        if user_id != OWNER_ID:
            return
        execute_query("DELETE FROM channel_links")
        await query.message.reply_text("✅ Kanal linki o'chirildi!")
        return

   # ---------- DO'STLARGA YUBORISH TUGMASI ----------
elif data == "share_friend":
    # Userning oxirgi ko'rgan video kodini olish
    last_code = context.user_data.get("last_video_code")
    if last_code:
        # Taklif xabarini yaratish
        share_text = "🎬 Sizga do'stingiz film yubordi!\n\n"
        share_text += "📽️ Filmlar bazasidan maxsus tanlangan video\n"
        share_text += "🎁 Bepul ko'rish imkoniyati\n\n"
        share_text += f"👉 Video ni ko'rish uchun quyidagi botga kirib 'START' tugmasini bosing:\n"
        share_text += f"{BOT_USERNAME}"
        
        # Textni URL encode qilish
        import urllib.parse
        encoded_text = urllib.parse.quote(share_text)
        
        # ✅ TO'G'RI TELEGRAM SHARE LINK
        share_url = f"https://t.me/share/url?text={encoded_text}"
        
        # Ulashish uchun maxsus keyboard
        keyboard = [
            [InlineKeyboardButton("📤 Do'stga yuborish", url=share_url)],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_video")]
        ]
        
        await query.message.reply_text(
            f"✅ Do'stingizga taklif yuborish uchun quyidagi tugmani bosing.\n\n"
            f"Do'stingiz botga start bosgandan so'ng video avtomatik ravishda ochiladi!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.message.reply_text("❌ Video kodi topilmadi. Iltimos, avval videoni ko'ring.")
    return

# ---------- ORQAGA TUGMASI ----------
elif data == "back_to_video":
    # Orqaga qaytish logikasi
    last_code = context.user_data.get("last_video_code")
    if last_code:
        # Video qayta yuborish
        result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (last_code,))
        if result:
            file_id, extra_text = result
            if last_code.startswith('http'):
                caption_text = f"Link: {last_code}\n{extra_text}\n{BOT_USERNAME}"
            else:
                caption_text = f"Kod: {last_code}\n{extra_text}\n{BOT_USERNAME}"
            
            await query.message.reply_video(file_id, caption=caption_text)
            
            # Tugmalarni qayta chiqarish
            await send_callback_buttons(query, context)
            
            # Xabarni qayta chiqarish
            await send_callback_caption(query, context)
    return

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID and not is_admin(update.message.from_user.id):
        return
    if not update.message.video:
        return
    
    action = context.user_data.get("action")
    
    # Broadcast uchun video
    if action == "broadcast":
        context.user_data["broadcast_video"] = update.message.video.file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Video qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return
    
    # BOSHQA HOLATLAR: Yangi video yuklash yoki action yo'q
    context.user_data.clear()  # Avvalgi ma'lumotlarni tozalash
    context.user_data["video_file_id"] = update.message.video.file_id
    context.user_data["action"] = "set_code"
    await update.message.reply_text("Video qabul qilindi! Endi video uchun kod yoki Instagram linkini yozing:")
    return

# ---------- OWNER PHOTO HANDLER ----------
async def handle_owner_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID and not is_admin(update.message.from_user.id):
        return
    
    action = context.user_data.get("action")
    
    if action == "broadcast":
        context.user_data["broadcast_photo"] = update.message.photo[-1].file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Rasm qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return

# ---------- PHOTO HANDLER (Chek qabul qilish) ----------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id == OWNER_ID or is_admin(user_id):
        await handle_owner_photo(update, context)
        return
    
    action = context.user_data.get("action")
    if action == "waiting_receipt":
        photo_file = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        
        if DATABASE_URL:
            execute_query("""
                INSERT INTO bypass_requests (user_id, request_text, status) 
                VALUES (%s, %s, 'pending')
                ON CONFLICT (user_id) DO UPDATE SET 
                request_text = EXCLUDED.request_text,
                request_date = CURRENT_TIMESTAMP,
                status = 'pending'
            """, (user_id, caption))
        else:
            execute_query("""
                INSERT OR REPLACE INTO bypass_requests (user_id, request_text, status) 
                VALUES (?, ?, 'pending')
            """, (user_id, caption))
        
        try:
            await context.bot.send_photo(
                OWNER_ID, 
                photo_file, 
                caption=f"📨 Yangi chek so'rovi!\nUser ID: {user_id}\nIzoh: {caption}\n\nPremium berish uchun /premium {user_id} 30 (30 kunlik)"
            )
        except Exception as e:
            print(f"Xatolik ownerga xabar yuborishda: {e}")
        
        await update.message.reply_text(
            "✅ Chek qabul qilindi! Admin tekshiradi va sizga premium beriladi. "
            "Tasdiqlash uchun biroz kuting."
        )
        context.user_data.clear()

# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")

    # ---------- OWNER ACTIONS ----------
    if user_id == OWNER_ID or is_admin(user_id):
        # Video kodi qo'shish (har qanday matn: asd123 yoki Instagram link)
        if action == "set_code":
            file_id = context.user_data.get("video_file_id")
            if not file_id:
                await update.message.reply_text("Xatolik! Avval video yuboring.")
                context.user_data.clear()
                return
            
            # Kod bandligini tekshirish (har qanday matn uchun)
            existing = fetch_one("SELECT * FROM films WHERE code=%s" if DATABASE_URL else "SELECT * FROM films WHERE code=?", (text,))
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod/link band! Boshqa kod yoki link kiriting:")
                return
                
            if DATABASE_URL:
                execute_query("INSERT INTO films (code, file_id) VALUES (%s, %s) ON CONFLICT (code) DO UPDATE SET file_id = EXCLUDED.file_id", (text, file_id))
            else:
                execute_query("INSERT OR REPLACE INTO films (code, file_id) VALUES (?, ?)", (text, file_id))
            
            result = fetch_one("SELECT extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT extra_text FROM films WHERE code=?", (text,))
            extra_text = result[0] if result else ""
            
            # Agar link bo'lsa, caption ni boshqacha ko'rsatish
            if text.startswith('http'):
                caption_text = f"Link: {text}\n{extra_text}\n{BOT_USERNAME}"
            else:
                caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            
            # Callback data uchun kodni qisqartirish
            safe_code = create_safe_callback_data(text)
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                 InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{safe_code}")]
            ]
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            await update.message.reply_text(f"✅ Video saqlandi! {'Link' if text.startswith('http') else 'Kod'}: {text}")
            
            context.user_data["video_file_id"] = None
            context.user_data["action"] = "upload_video"
            return

        # Video kodi qidirish
        if action == "search_video":
            result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (text,))
            if result:
                file_id, extra_text = result
                # Agar link bo'lsa, caption ni boshqacha ko'rsatish
                if text.startswith('http'):
                    caption_text = f"Link: {text}\n{extra_text}\n{BOT_USERNAME}"
                else:
                    caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                
                safe_code = create_safe_callback_data(text)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                     InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{safe_code}")]
                ]
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            else:
                await update.message.reply_text("Bunday kod/linkka film topilmadi!")
            context.user_data.clear()
            return

        # Kanal qo'shish
        if action == "add_channel":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            if DATABASE_URL:
                execute_query("INSERT INTO channels (channel) VALUES (%s) ON CONFLICT (channel) DO NOTHING", (text,))
            else:
                execute_query("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            await update.message.reply_text(f"Kanal qo'shildi: {text}")
            context.user_data.clear()
            return

        # Kanal o'chirish
        if action == "delete_channel":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            execute_query("DELETE FROM channels WHERE channel=%s" if DATABASE_URL else "DELETE FROM channels WHERE channel=?", (text,))
            await update.message.reply_text(f"Kanal o'chirildi: {text}")
            context.user_data.clear()
            return

        # Broadcast tasdiqlash
        if action == "confirm_broadcast":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            if text.upper() == "HA":
                users = fetch_all("SELECT user_id FROM users")
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
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            users = fetch_all("SELECT user_id FROM users")
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
            execute_query("UPDATE films SET extra_text=%s" if DATABASE_URL else "UPDATE films SET extra_text=?", (text,))
            await update.message.reply_text("Qo'shimcha matn barcha videolarga qo'shildi!")
            context.user_data.clear()
            return

        # Qo'shimcha matn barcha videolardan o'chirish
        if action == "delete_extra":
            execute_query("UPDATE films SET extra_text=%s" if DATABASE_URL else "UPDATE films SET extra_text=?", ('',))
            await update.message.reply_text("Qo'shimcha matn barcha videolardan o'chirildi!")
            context.user_data.clear()
            return

        # Owner kodi alishtirish
        if action == "update_code":
            new_code = text
            old_code = context.user_data.get("old_code")
            
            existing = fetch_one("SELECT * FROM films WHERE code=%s AND code != %s" if DATABASE_URL else "SELECT * FROM films WHERE code=? AND code!=?", (new_code, old_code))
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod band! Boshqa kod kiriting:")
                return
                
            execute_query("UPDATE films SET code=%s WHERE code=%s" if DATABASE_URL else "UPDATE films SET code=? WHERE code=?", (new_code, old_code))
            result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (new_code,))
            if result:
                file_id, extra_text = result
                # Agar link bo'lsa, caption ni boshqacha ko'rsatish
                if new_code.startswith('http'):
                    caption_text = f"Link: {new_code}\n{extra_text}\n{BOT_USERNAME}"
                else:
                    caption_text = f"Kod: {new_code}\n{extra_text}\n{BOT_USERNAME}"
                
                safe_code = create_safe_callback_data(new_code)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                     InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{safe_code}")]
                ]
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            await update.message.reply_text(f"Video kodi yangilandi! Yangi kod: {new_code}")
            context.user_data.clear()
            return

        # Hamkor qo'shish
        if action == "add_partner":
            execute_query("INSERT INTO partners (text) VALUES (%s)" if DATABASE_URL else "INSERT INTO partners (text) VALUES (?)", (text,))
            await update.message.reply_text(f"Hamkor qo'shildi: {text}")
            context.user_data.clear()
            return

        # Hamkor o'chirish
        if action == "delete_partner":
            try:
                partner_num = int(text)
                partners = fetch_all("SELECT id FROM partners ORDER BY id")
                if 1 <= partner_num <= len(partners):
                    partner_id = partners[partner_num-1][0]
                    execute_query("DELETE FROM partners WHERE id=%s" if DATABASE_URL else "DELETE FROM partners WHERE id=?", (partner_id,))
                    await update.message.reply_text(f"Hamkor #{partner_num} o'chirildi!")
                else:
                    await update.message.reply_text("Noto'g'ri raqam!")
            except ValueError:
                await update.message.reply_text("Iltimos, raqam kiriting!")
            context.user_data.clear()
            return

        # Reklama matnini o'zgartirish
        if action == "edit_ad_text":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            execute_query("INSERT INTO ad_texts (text) VALUES (%s)" if DATABASE_URL else "INSERT INTO ad_texts (text) VALUES (?)", (text,))
            await update.message.reply_text("✅ Reklama matni yangilandi!")
            context.user_data.clear()
            return

        # So'rovlarni boshqarish
        elif action == "manage_requests":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                target_user_id = int(text)
                existing = fetch_one("SELECT * FROM bypass_requests WHERE user_id=%s" if DATABASE_URL else "SELECT * FROM bypass_requests WHERE user_id=?", (target_user_id,))
                if existing:
                    context.user_data["action"] = "set_premium_days"
                    context.user_data["target_user"] = target_user_id
                    await update.message.reply_text(f"User {target_user_id} uchun premium kunlar sonini kiriting (masalan, 30):")
                else:
                    await update.message.reply_text("Bu user ID bo'yicha so'rov topilmadi.")
            except ValueError:
                await update.message.reply_text("Iltimos, to'g'ri user ID kiriting.")
            return

        # Premium kunlarini belgilash
        elif action == "set_premium_days":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                days = int(text)
                target_user_id = context.user_data.get("target_user")
                
                if target_user_id and days > 0:
                    expiry_date = datetime.now() + timedelta(days=days)
                    
                    if DATABASE_URL:
                        execute_query("""
                            INSERT INTO premium_users (user_id, expiry_date, approved_by, approved_date) 
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (user_id) DO UPDATE SET 
                            expiry_date = EXCLUDED.expiry_date,
                            approved_by = EXCLUDED.approved_by,
                            approved_date = EXCLUDED.approved_date
                        """, (target_user_id, expiry_date, OWNER_ID, datetime.now()))
                    else:
                        execute_query("""
                            INSERT OR REPLACE INTO premium_users (user_id, expiry_date, approved_by, approved_date) 
                            VALUES (?, ?, ?, ?)
                        """, (target_user_id, expiry_date.isoformat(), OWNER_ID, datetime.now().isoformat()))
                    
                    execute_query("DELETE FROM bypass_requests WHERE user_id=%s" if DATABASE_URL else "DELETE FROM bypass_requests WHERE user_id=?", (target_user_id,))
                    
                    try:
                        await context.bot.send_message(
                            target_user_id, 
                            f"🎉 Tabriklaymiz! Sizga {days} kunlik premium berildi!\n"
                            f"Endi siz kanallarga obuna bo'lish shartisiz botdan foydalana olasiz.\n\n"
                            f"Premium muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}\n"
                            f"Botdan foydalanish: /start"
                        )
                    except Exception as e:
                        print(f"Userga xabar yuborishda xatolik: {e}")
                    
                    await update.message.reply_text(
                        f"✅ User {target_user_id} ga {days} kunlik premium berildi!\n"
                        f"Muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                    )
                else:
                    await update.message.reply_text("Xatolik! Iltimos, qaytadan urining.")
            except ValueError:
                await update.message.reply_text("Iltimos, kunlar sonini raqamda kiriting.")
            context.user_data.clear()
            return

        # Userga premium berish
        elif action == "give_premium_user":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                target_user_id = int(text)
                context.user_data["action"] = "set_premium_days_direct"
                context.user_data["target_user"] = target_user_id
                await update.message.reply_text(f"User {target_user_id} uchun premium kunlar sonini kiriting:")
            except ValueError:
                await update.message.reply_text("Iltimos, to'g'ri user ID kiriting.")
            return

        # To'g'ridan-to'g'ri premium kunlarini belgilash
        elif action == "set_premium_days_direct":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                days = int(text)
                target_user_id = context.user_data.get("target_user")
                
                if target_user_id and days > 0:
                    expiry_date = datetime.now() + timedelta(days=days)
                    
                    if DATABASE_URL:
                        execute_query("""
                            INSERT INTO premium_users (user_id, expiry_date, approved_by, approved_date) 
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (user_id) DO UPDATE SET 
                            expiry_date = EXCLUDED.expiry_date,
                            approved_by = EXCLUDED.approved_by,
                            approved_date = EXCLUDED.approved_date
                        """, (target_user_id, expiry_date, OWNER_ID, datetime.now()))
                    else:
                        execute_query("""
                            INSERT OR REPLACE INTO premium_users (user_id, expiry_date, approved_by, approved_date) 
                            VALUES (?, ?, ?, ?)
                        """, (target_user_id, expiry_date.isoformat(), OWNER_ID, datetime.now().isoformat()))
                    
                    await update.message.reply_text(
                        f"✅ User {target_user_id} ga {days} kunlik premium berildi!\n"
                        f"Muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                    )
                else:
                    await update.message.reply_text("Xatolik! Iltimos, qaytadan urining.")
            except ValueError:
                await update.message.reply_text("Iltimos, kunlar sonini raqamda kiriting.")
            context.user_data.clear()
            return

        # Premiumni olib tashlash
        elif action == "remove_premium_user":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                target_user_id = int(text)
                execute_query("DELETE FROM premium_users WHERE user_id=%s" if DATABASE_URL else "DELETE FROM premium_users WHERE user_id=?", (target_user_id,))
                await update.message.reply_text(f"✅ User {target_user_id} ning premiumi olib tashlandi!")
            except ValueError:
                await update.message.reply_text("Iltimos, to'g'ri user ID kiriting.")
            context.user_data.clear()
            return

        # YANGI: Admin qo'shish
        elif action == "add_admin":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                admin_id = int(text)
                if DATABASE_URL:
                    execute_query("INSERT INTO admins (user_id, added_by) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", (admin_id, user_id))
                else:
                    execute_query("INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)", (admin_id, user_id))
                await update.message.reply_text(f"✅ User {admin_id} admin qilindi!")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri user ID kiriting!")
            context.user_data.clear()
            return

        # YANGI: Adminni o'chirish
        elif action == "remove_admin":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            try:
                admin_id = int(text)
                execute_query("DELETE FROM admins WHERE user_id=%s" if DATABASE_URL else "DELETE FROM admins WHERE user_id=?", (admin_id,))
                await update.message.reply_text(f"✅ Admin {admin_id} o'chirildi!")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri user ID kiriting!")
            context.user_data.clear()
            return

        # YANGI: Video caption qo'shish
        elif action == "add_video_caption":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            execute_query("INSERT INTO video_captions (caption_text) VALUES (%s)" if DATABASE_URL else "INSERT INTO video_captions (caption_text) VALUES (?)", (text,))
            await update.message.reply_text("✅ Video xabari saqlandi! Endi barcha videolardan keyin bu xabar chiqadi.")
            context.user_data.clear()
            return

        # YANGI: Video button matnini qo'shish
        elif action == "add_video_button_text":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            context.user_data["button_text"] = text
            context.user_data["action"] = "add_video_button_url"
            await update.message.reply_text("Endi tugma linkini yozing:")
            return

        # YANGI: Video button linkini qo'shish
        elif action == "add_video_button_url":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            button_text = context.user_data.get("button_text")
            if button_text:
                execute_query("INSERT INTO video_buttons (button_text, button_url) VALUES (%s, %s)" if DATABASE_URL else "INSERT INTO video_buttons (button_text, button_url) VALUES (?, ?)", (button_text, text))
                await update.message.reply_text(f"✅ Video tugmasi saqlandi!\nMatn: {button_text}\nLink: {text}")
            context.user_data.clear()
            return

        # YANGI: Channel link matnini qo'shish
        elif action == "add_channel_link_text":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            context.user_data["link_text"] = text
            context.user_data["action"] = "add_channel_link_url"
            await update.message.reply_text("Endi link manzilini yozing:")
            return

        # YANGI: Channel link URL ni qo'shish
        elif action == "add_channel_link_url":
            if user_id != OWNER_ID:
                await update.message.reply_text("❌ Bu funksiya faqat owner uchun!")
                return
            link_text = context.user_data.get("link_text")
            if link_text:
                execute_query("INSERT INTO channel_links (link_text, link_url) VALUES (%s, %s)" if DATABASE_URL else "INSERT INTO channel_links (link_text, link_url) VALUES (?, ?)", (link_text, text))
                await update.message.reply_text(f"✅ Kanal linki saqlandi!\nMatn: {link_text}\nLink: {text}")
            context.user_data.clear()
            return

    # ---------- FOYDALANUVCHI KINO KO'RISH ----------
    # User har qanday matn yuborsa (asd123 yoki Instagram link), video qidirish
    result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (text,))
    if result:
        file_id, extra_text = result
        
        context.user_data["last_video_code"] = text
        
        is_premium = is_premium_user(user_id)
        
        if is_premium:
            # Agar link bo'lsa, caption ni boshqacha ko'rsatish
            if text.startswith('http'):
                caption_text = f"Link: {text}\n{extra_text}\n{BOT_USERNAME}"
            else:
                caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
            
            await update.message.reply_video(file_id, caption=caption_text)
            
            # ✅ HAR DOIM TUGMALAR CHIQSIN
            await send_video_buttons(update, context)
            
            # ✅ HAR DOIM XABAR CHIQSIN
            await send_video_caption(update, context)
            
        else:
            channels = fetch_all("SELECT channel FROM channels")
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
                
                # Kanal linkini qo'shish
                link_result = fetch_one("SELECT link_text, link_url FROM channel_links ORDER BY id DESC LIMIT 1")
                if link_result:
                    link_text, link_url = link_result
                    keyboard.append([InlineKeyboardButton(link_text, url=link_url)])
                
                safe_code = create_safe_callback_data(text)
                keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{safe_code}")])
                keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
                
                await update.message.reply_text(
                    "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Agar link bo'lsa, caption ni boshqacha ko'rsatish
                if text.startswith('http'):
                    caption_text = f"Link: {text}\n{extra_text}\n{BOT_USERNAME}"
                else:
                    caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                
                await update.message.reply_video(file_id, caption=caption_text)
                
                # ✅ HAR DOIM TUGMALAR CHIQSIN
                await send_video_buttons(update, context)
                
                # ✅ HAR DOIM XABAR CHIQSIN
                await send_video_caption(update, context)
    else:
        # Agar video topilmasa
        await update.message.reply_text("Bunday kod/linkka film topilmadi! Iltimos, to'g'ri kod yoki linkni yuboring.")

# ---------- COMMAND HANDLER QO'SHIMCHALARI ----------
async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner uchun premium berish command"""
    if update.message.from_user.id != OWNER_ID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Foydalanish: /premium [user_id] [kunlar]")
        return
    
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        
        expiry_date = datetime.now() + timedelta(days=days)
        if DATABASE_URL:
            execute_query("""
                INSERT INTO premium_users (user_id, expiry_date, approved_by, approved_date) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET 
                expiry_date = EXCLUDED.expiry_date,
                approved_by = EXCLUDED.approved_by,
                approved_date = EXCLUDED.approved_date
            """, (user_id, expiry_date, OWNER_ID, datetime.now()))
        else:
            execute_query("""
                INSERT OR REPLACE INTO premium_users (user_id, expiry_date, approved_by, approved_date) 
                VALUES (?, ?, ?, ?)
            """, (user_id, expiry_date.isoformat(), OWNER_ID, datetime.now().isoformat()))
        
        await update.message.reply_text(
            f"✅ User {user_id} ga {days} kunlik premium berildi!\n"
            f"Muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
        )
        
        try:
            await context.bot.send_message(
                user_id, 
                f"🎉 Tabriklaymiz! Sizga {days} kunlik premium berildi!\n"
                f"Endi siz kanallarga obuna bo'lish shartisiz botdan foydalana olasiz."
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text("Xatolik! User ID va kunlar sonini to'g'ri kiriting.")

# ---------- APPLICATION ----------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("premium", premium_command))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == '__main__':
    print("Bot ishga tushdi...")
    app.run_polling()

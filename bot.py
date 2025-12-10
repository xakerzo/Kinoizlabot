from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, InlineQueryHandler, ChosenInlineResultHandler
import urllib.parse
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timedelta
import hashlib
import re

# ---------- TOKEN VA OWNER ----------
OWNER_ID = 1373647
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8505113284:AAFu0vhU6j7d4tsaY5Rsn1qga57THZt3pEo")
BOT_USERNAME = "@kinoni_izlabot"
BOT_LINK = "https://t.me/kinoni_izlabot"

# ---------- YANGI OWNER TUGMA TIZIMI ----------
OWNER_KEYBOARD = {
    "main": [
        ["📤 Video yuklash", "🔍 Video qidirish"],
        ["🎬 Premium video", "📢 Broadcast"],
        ["📺 Majburiy kanal", "📝 Video ostidagi matn"],
        ["🔤 Startdagi xabar", "⭐ Premium matn"],
        ["🎫 Premium boshqaruv", "📊 Statistika"],
        ["👥 Bot foydalanuvchilari"]
    ],
    "video_actions": [
        ["📤 Video yuklash", "🔍 Video qidirish"],
        ["⬅️ Ortga"]
    ],
    "premium_video_actions": [
        ["🎬 Premium video yuklash", "🔍 Premium video qidirish"],
        ["⬅️ Ortga"]
    ],
    "broadcast_actions": [
        ["📢 Rasm + Text", "📹 Video + Text"],
        ["✏️ Faqat text", "⬅️ Ortga"]
    ],
    "channel_actions": [
        ["➕ Kanal qo'shish", "🔍 Kanallarni tekshirish"],
        ["🗑 Kanal o'chirish", "⬅️ Ortga"]
    ],
    "video_caption_actions": [
        ["📝 Matn qo'shish", "🔍 Matnni tekshirish"],
        ["🗑 Matnni o'chirish", "⬅️ Ortga"]
    ],
    "start_message_actions": [
        ["📝 Matn qo'shish", "🔍 Matnni tekshirish"],
        ["🗑 Matnni o'chirish", "⬅️ Ortga"]
    ],
    "premium_text_actions": [
        ["📝 Matn qo'shish", "🔍 Matnni tekshirish"],
        ["🖼️ Rasm + Matn", "🗑 Matnni o'chirish"],
        ["⬅️ Ortga"]
    ],
    "premium_management_actions": [
        ["👤 Userga premium berish", "📋 Premium foydalanuvchilar"],
        ["🗑 Premiumni olib tashlash", "⬅️ Ortga"]
    ]
}

# ---------- YANGI FUNKSIYA: INSTAGRAM LINKINI TOZALASH ----------
def clean_instagram_url(url):
    """Instagram linkini to'g'ri shaklga keltirish"""
    if 'instagram.com' not in url.lower():
        return url
    
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+)'
    
    match = re.search(pattern, url)
    if match:
        clean_url = match.group(1)
        if clean_url.endswith('/'):
            clean_url = clean_url[:-1]
        return clean_url
    
    return url

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
            caption TEXT DEFAULT '',
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_captions (
            id SERIAL PRIMARY KEY,
            caption_text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS start_messages (
            id SERIAL PRIMARY KEY,
            message_text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_texts (
            id SERIAL PRIMARY KEY,
            text TEXT,
            photo_id TEXT,
            caption TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_videos (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            caption TEXT DEFAULT '',
            extra_text TEXT DEFAULT '',
            is_premium BOOLEAN DEFAULT TRUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_stats (
            code TEXT PRIMARY KEY,
            views INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS total_stats (
            id INTEGER PRIMARY KEY DEFAULT 1,
            total_videos INTEGER DEFAULT 0,
            total_views INTEGER DEFAULT 0,
            CONSTRAINT single_row CHECK (id = 1)
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
            caption TEXT DEFAULT '',
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_captions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caption_text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS start_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_text TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            photo_id TEXT,
            caption TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premium_videos (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            caption TEXT DEFAULT '',
            extra_text TEXT DEFAULT '',
            is_premium BOOLEAN DEFAULT TRUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_stats (
            code TEXT PRIMARY KEY,
            views INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS total_stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_videos INTEGER DEFAULT 0,
            total_views INTEGER DEFAULT 0
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
    
    if isinstance(expiry_date, datetime):
        return expiry_date > datetime.now()
    else:
        return datetime.fromisoformat(expiry_date) > datetime.now()

# ---------- STATISTIKA FUNKSIYALARI ----------
def update_video_stats(code):
    """Video ko'rilish statistikasini yangilash"""
    result = fetch_one("SELECT views FROM video_stats WHERE code=%s" if DATABASE_URL else "SELECT views FROM video_stats WHERE code=?", (code,))
    
    if result:
        new_views = result[0] + 1
        execute_query("UPDATE video_stats SET views=%s WHERE code=%s" if DATABASE_URL else "UPDATE video_stats SET views=? WHERE code=?", (new_views, code))
    else:
        execute_query("INSERT INTO video_stats (code, views) VALUES (%s, 1)" if DATABASE_URL else "INSERT INTO video_stats (code, views) VALUES (?, 1)", (code,))
    
    total_result = fetch_one("SELECT total_videos, total_views FROM total_stats WHERE id=1")
    if total_result:
        total_videos, total_views = total_result
        execute_query("UPDATE total_stats SET total_views=%s WHERE id=1" if DATABASE_URL else "UPDATE total_stats SET total_views=? WHERE id=1", (total_views + 1,))
    else:
        execute_query("INSERT INTO total_stats (id, total_videos, total_views) VALUES (1, 0, 1)" if DATABASE_URL else "INSERT INTO total_stats (id, total_videos, total_views) VALUES (1, 0, 1)")

def update_total_videos_count():
    """Jami videolar sonini yangilash"""
    films_count = fetch_one("SELECT COUNT(*) FROM films")[0]
    premium_count = fetch_one("SELECT COUNT(*) FROM premium_videos")[0]
    total_count = films_count + premium_count
    
    total_result = fetch_one("SELECT total_videos FROM total_stats WHERE id=1")
    if total_result:
        execute_query("UPDATE total_stats SET total_videos=%s WHERE id=1" if DATABASE_URL else "UPDATE total_stats SET total_videos=? WHERE id=1", (total_count,))
    else:
        execute_query("INSERT INTO total_stats (id, total_videos, total_views) VALUES (1, %s, 0)" if DATABASE_URL else "INSERT INTO total_stats (id, total_videos, total_views) VALUES (1, ?, 0)", (total_count,))

def get_total_stats():
    """Umumiy statistikani olish"""
    result = fetch_one("SELECT total_videos, total_views FROM total_stats WHERE id=1")
    if result:
        return result[0], result[1]
    return 0, 0

def get_video_stats(code):
    """Video statistikasini olish"""
    result = fetch_one("SELECT views FROM video_stats WHERE code=%s" if DATABASE_URL else "SELECT views FROM video_stats WHERE code=?", (code,))
    if result:
        return result[0]
    return 0

# ---------- VIDEO OSTIDAGI MATN FUNKSIYALARI ----------
async def send_video_caption(update: Update, context: ContextTypes.DEFAULT_TYPE, video_code=None):
    """Video dan keyin matn yuborish"""
    try:
        if not video_code:
            video_code = context.user_data.get("last_video_code")
        
        if not video_code:
            return
        
        caption_result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        
        if caption_result:
            keyboard = [
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await update.message.reply_text(
                caption_result[0],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await update.message.reply_text(
                "Quyidagi tugmalardan foydalaning:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        print(f"Matn yuborishda xatolik: {e}")

async def send_callback_caption(query, context: ContextTypes.DEFAULT_TYPE, video_code=None):
    """Callback uchun video matnini yuborish"""
    try:
        if not video_code:
            video_code = context.user_data.get("last_video_code")
        
        if not video_code:
            return
        
        caption_result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        
        if caption_result:
            keyboard = [
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await query.message.reply_text(
                caption_result[0],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [
                [InlineKeyboardButton("👥 Do'stlarga yuborish", callback_data="share_friend")]
            ]
            await query.message.reply_text(
                "Quyidagi tugmalardan foydalaning:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        print(f"Callback matn yuborishda xatolik: {e}")

# ---------- CALLBACK DATA YORDAMCHI FUNKSIYALARI ----------
def create_safe_callback_data(code):
    """Uzun kodlar uchun xavfsiz callback data yaratish"""
    if len(code) > 50:
        hash_object = hashlib.md5(code.encode())
        short_code = hash_object.hexdigest()[:10]
    else:
        short_code = code
    return short_code

def get_original_code_from_callback(short_code):
    """Qisqartirilgan kod orqali asl kodni topish"""
    films = fetch_all("SELECT code FROM films")
    for film in films:
        original_code = film[0]
        if create_safe_callback_data(original_code) == short_code:
            return original_code
    
    premium_films = fetch_all("SELECT code FROM premium_videos")
    for film in premium_films:
        original_code = film[0]
        if create_safe_callback_data(original_code) == short_code:
            return original_code
    
    return short_code

# ---------- DO'STLARGA YUBORISH FUNKSIYALARI ----------
async def start_share_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Do'stlarga yuborishni boshlash"""
    query = update.callback_query
    user_id = query.from_user.id
    
    last_code = context.user_data.get("last_video_code")
    if not last_code:
        await query.answer("❌ Video kodi topilmadi. Iltimos, avval videoni ko'ring.", show_alert=True)
        return
    
    result = fetch_one("SELECT file_id FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id FROM films WHERE code=?", (last_code,))
    if not result:
        await query.answer("❌ Video topilmadi.", show_alert=True)
        return
    
    await query.message.reply_text(
        f"🎬 Video ulashish\n\n"
        f"📹 Video: {last_code}\n\n"
        f"Do'stlaringizga video yuborish uchun quyidagi tugmani bosing:"
    )
    
    await query.message.reply_text(
        "📤 Do'stingizga video yuborish uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📤 Do'stlarga yuborish", switch_inline_query="")
        ]])
    )

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline query handler - do'stlarga yuborish"""
    query = update.inline_query
    user_id = query.from_user.id
    
    last_code = context.user_data.get("last_video_code")
    if not last_code:
        films = fetch_all("SELECT code FROM films ORDER BY code LIMIT 10")
        if not films:
            return
        
        results = []
        for film in films:
            video_code = film[0]
            
            share_text = f"🎬 Do'stim sizga video yubordi!\n\n"
            if video_code.startswith('http'):
                share_text += f"🔗 Link: {video_code}\n"
            else:
                share_text += f"📹 Video kod: {video_code}\n"
            share_text += f"🤖 Bot: {BOT_USERNAME}\n\n"
            share_text += f"Video ni ko'rish uchun quyidagi tugmani bosing 👇"
            
            keyboard = [
                [InlineKeyboardButton("🎬 Videoni ko'rish", url=f"{BOT_LINK}?start={urllib.parse.quote(video_code)}")]
            ]
            
            results.append(
                InlineQueryResultArticle(
                    id=hashlib.md5(video_code.encode()).hexdigest()[:64],
                    title=f"📹 Video: {video_code[:30]}{'...' if len(video_code) > 30 else ''}",
                    description=f"Do'stingizga video yuboring - {video_code}",
                    input_message_content=InputTextMessageContent(
                        message_text=share_text
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            )
        
        await query.answer(results)
        return
    
    result = fetch_one("SELECT file_id FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id FROM films WHERE code=?", (last_code,))
    if not result:
        return
    
    share_text = f"🎬 Do'stim sizga video yubordi!\n\n"
    if last_code.startswith('http'):
        share_text += f"🔗 Link: {last_code}\n"
    else:
        share_text += f"📹 Video kod: {last_code}\n"
    share_text += f"🤖 Bot: {BOT_USERNAME}\n\n"
    share_text += f"Video ni ko'rish uchun quyidagi tugmani bosing 👇"
    
    keyboard = [
        [InlineKeyboardButton("🎬 Videoni ko'rish", url=f"{BOT_LINK}?start={urllib.parse.quote(last_code)}")]
    ]
    
    results = [
        InlineQueryResultArticle(
            id=hashlib.md5(last_code.encode()).hexdigest()[:64],
            title="📤 Do'stingizga video yuboring",
            description=f"Video: {last_code}",
            input_message_content=InputTextMessageContent(
                message_text=share_text
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    ]
    
    await query.answer(results)

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tanlangan inline result - do'stga yuborilganda"""
    chosen_result = update.chosen_inline_result
    user_id = chosen_result.from_user.id
    result_id = chosen_result.result_id
    
    last_code = context.user_data.get("last_video_code")
    if last_code:
        context.user_data.setdefault("shared_count", 0)
        context.user_data["shared_count"] += 1
        
        try:
            await context.bot.send_message(
                user_id,
                f"✅ Video {last_code} do'stingizga yuborildi!\n"
                f"Jami yuborilgan do'stlar: {context.user_data['shared_count']}"
            )
        except:
            pass

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    
    if DATABASE_URL:
        execute_query("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    else:
        execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    if args and len(args) > 0:
        video_code = urllib.parse.unquote(args[0])
        
        # Premium video tekshirish
        premium_result = fetch_one("SELECT file_id, caption, extra_text FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM premium_videos WHERE code=?", (video_code,))
        
        if premium_result:
            file_id, video_caption, extra_text = premium_result
            is_premium = is_premium_user(user_id)
            
            if is_premium:
                context.user_data["last_video_code"] = video_code
                update_video_stats(video_code)
                video_views = get_video_stats(video_code)
                
                if video_caption:
                    caption_with_stats = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
                else:
                    caption_with_stats = f"🎬 Premium video\n📹 Kod: {video_code}\n\n👁️ Ko'rishlar: {video_views}"
                
                await update.message.reply_video(file_id, caption=caption_with_stats)
                await send_video_caption(update, context)
                return
            else:
                premium_text_result = fetch_one("SELECT text, photo_id, caption FROM premium_texts ORDER BY id DESC LIMIT 1")
                if premium_text_result:
                    premium_text, photo_id, caption = premium_text_result
                    if photo_id:
                        await update.message.reply_photo(photo_id, caption=caption)
                    elif premium_text:
                        await update.message.reply_text(premium_text)
                
                await update.message.reply_text(
                    "❗ Bu video faqat premium foydalanuvchilar uchun!\n"
                    "Premium olish uchun admin bilan bog'laning."
                )
                return
        
        # Oddiy video tekshirish
        result = fetch_one("SELECT file_id, caption, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM films WHERE code=?", (video_code,))
        
        if result:
            file_id, video_caption, extra_text = result
            context.user_data["last_video_code"] = video_code
            update_video_stats(video_code)
            video_views = get_video_stats(video_code)
            
            is_premium = is_premium_user(user_id)
            
            if video_caption:
                caption_with_stats = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
            else:
                if video_code.startswith('http'):
                    caption_with_stats = f"🔗 Link: {video_code}\n\n👁️ Ko'rishlar: {video_views}"
                else:
                    caption_with_stats = f"📹 Kod: {video_code}\n\n👁️ Ko'rishlar: {video_views}"
            
            if is_premium:
                await update.message.reply_video(file_id, caption=caption_with_stats)
                await send_video_caption(update, context)
                return
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
                    
                    safe_code = create_safe_callback_data(video_code)
                    keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{safe_code}")])
                    keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
                    
                    await update.message.reply_text(
                        "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_video(file_id, caption=caption_with_stats)
                    await send_video_caption(update, context)
            
            return

    # Start xabarini olish
    start_result = fetch_one("SELECT message_text FROM start_messages ORDER BY id DESC LIMIT 1")
    
    # Hamkorlar matnini olish
    partners_texts = fetch_all("SELECT text FROM partners ORDER BY id")
    
    if start_result:
        start_message = start_result[0]
        if partners_texts:
            start_message += "\n\n🤝 Hamkorlarimiz:\n" + "\n".join([text[0] for text in partners_texts])
    else:
        start_message = "Salom! Kino kodi yoki Instagram linkini kiriting:"
        if partners_texts:
            start_message += "\n\n🤝 Hamkorlarimiz:\n" + "\n".join([text[0] for text in partners_texts])
    
    # Owner uchun yangi interfeys
    if user_id == OWNER_ID:
        keyboard = []
        for row in OWNER_KEYBOARD["main"]:
            keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_{btn.split()[0].lower()}") for btn in row])
        
        user_count = fetch_one("SELECT COUNT(*) FROM users")[0]
        keyboard.append([InlineKeyboardButton(f"👥 Foydalanuvchilar: {user_count}", callback_data="owner_users")])
        
        await update.message.reply_text("👑 Owner paneli:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Oddiy foydalanuvchilar uchun start xabari
    await update.message.reply_text(start_message)

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

    # ---------- DO'STLARGA YUBORISH TUGMASI ----------
    if data == "share_friend":
        await start_share_friend(update, context)
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
        
        is_premium = is_premium_user(user_id)
        
        if is_premium:
            result = fetch_one("SELECT file_id, caption, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM films WHERE code=?", (code,))
            if result:
                file_id, video_caption, extra_text = result
                update_video_stats(code)
                video_views = get_video_stats(code)
                
                if video_caption:
                    caption_with_stats = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
                else:
                    if code.startswith('http'):
                        caption_with_stats = f"🔗 Link: {code}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_with_stats = f"📹 Kod: {code}\n\n👁️ Ko'rishlar: {video_views}"
                
                await query.message.reply_video(file_id, caption=caption_with_stats)
                context.user_data["last_video_code"] = code
                await send_callback_caption(query, context)
            return

        result = fetch_one("SELECT file_id, caption, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM films WHERE code=?", (code,))
        if not result:
            await query.message.reply_text("Bunday kod/linkka film topilmadi!")
            return
        file_id, video_caption, extra_text = result

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
            
            safe_code = create_safe_callback_data(code)
            keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{safe_code}")])
            keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
            
            await query.message.reply_text(
                "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            update_video_stats(code)
            video_views = get_video_stats(code)
            
            if video_caption:
                caption_with_stats = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
            else:
                if code.startswith('http'):
                    caption_with_stats = f"🔗 Link: {code}\n\n👁️ Ko'rishlar: {video_views}"
                else:
                    caption_with_stats = f"📹 Kod: {code}\n\n👁️ Ko'rishlar: {video_views}"
            
            await query.message.reply_video(file_id, caption=caption_with_stats)
            context.user_data["last_video_code"] = code
            await send_callback_caption(query, context)
        return

    # ---------- OWNER PANEL TUGMALARI ----------
    if data.startswith("owner_"):
        action = data.replace("owner_", "")
        
        if user_id != OWNER_ID:
            await query.answer("❌ Bu funksiya faqat owner uchun!")
            return
        
        if action == "📤":
            keyboard = []
            for row in OWNER_KEYBOARD["video_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("📤 Video boshqarish:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "🎬":
            keyboard = []
            for row in OWNER_KEYBOARD["premium_video_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("🎬 Premium video boshqarish:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "📢":
            keyboard = []
            for row in OWNER_KEYBOARD["broadcast_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("📢 Broadcast yuborish:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "📺":
            keyboard = []
            for row in OWNER_KEYBOARD["channel_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("📺 Majburiy kanallar:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "📝":
            keyboard = []
            for row in OWNER_KEYBOARD["video_caption_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("📝 Video ostidagi matn:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "🔤":
            keyboard = []
            for row in OWNER_KEYBOARD["start_message_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("🔤 Startdagi xabar:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "⭐":
            keyboard = []
            for row in OWNER_KEYBOARD["premium_text_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("⭐ Premium matn:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "🎫":
            keyboard = []
            for row in OWNER_KEYBOARD["premium_management_actions"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_action_{btn.split()[0].lower()}") for btn in row])
            
            await query.message.edit_text("🎫 Premium boshqaruv:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "📊":
            total_videos, total_views = get_total_stats()
            
            top_videos = fetch_all("SELECT code, views FROM video_stats ORDER BY views DESC LIMIT 10")
            
            stats_text = f"📊 Bot statistikalari:\n\n"
            stats_text += f"📁 Jami videolar: {total_videos} ta\n"
            stats_text += f"👁️ Jami ko'rishlar: {total_views}\n"
            
            if top_videos:
                stats_text += f"\n🔥 Top 10 video:\n"
                for i, video in enumerate(top_videos, 1):
                    video_code, views = video
                    short_name = video_code[:20] + "..." if len(video_code) > 20 else video_code
                    stats_text += f"{i}. {short_name} - {views} 👁️\n"
            
            await query.message.edit_text(stats_text)
            return
        
        elif action == "users":
            user_count = fetch_one("SELECT COUNT(*) FROM users")[0]
            await query.message.edit_text(f"👥 Botdagi foydalanuvchilar soni: {user_count}")
            return
    
    # ---------- OWNER ACTION TUGMALARI ----------
    elif data.startswith("owner_action_"):
        action = data.replace("owner_action_", "")
        
        if user_id != OWNER_ID:
            return
        
        context.user_data.clear()
        
        if action == "ortga":
            keyboard = []
            for row in OWNER_KEYBOARD["main"]:
                keyboard.append([InlineKeyboardButton(btn, callback_data=f"owner_{btn.split()[0].lower()}") for btn in row])
            
            user_count = fetch_one("SELECT COUNT(*) FROM users")[0]
            keyboard.append([InlineKeyboardButton(f"👥 Foydalanuvchilar: {user_count}", callback_data="owner_users")])
            
            await query.message.edit_text("👑 Owner paneli:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        elif action == "yuklash":
            context.user_data["action"] = "upload_video"
            await query.message.edit_text("📤 Oddiy video yuboring (caption bilan yoki captionsiz):")
            return
        
        elif action == "qidirish":
            context.user_data["action"] = "search_video"
            await query.message.edit_text("🔍 Qidiriladigan kod yoki linkni yozing:")
            return
        
        elif action == "premium":
            context.user_data["action"] = "upload_premium_video"
            await query.message.edit_text("🎬 Premium video yuboring (caption bilan yoki captionsiz):")
            return
        
        elif action == "video":
            context.user_data["action"] = "search_premium_video"
            await query.message.edit_text("🔍 Premium video kodini yozing:")
            return
        
        elif action == "rasm":
            context.user_data["action"] = "broadcast_photo"
            await query.message.edit_text("📢 Broadcast uchun rasm yuboring:")
            return
        
        elif action == "video+text":
            context.user_data["action"] = "broadcast_video"
            await query.message.edit_text("📢 Broadcast uchun video yuboring:")
            return
        
        elif action == "faqat":
            context.user_data["action"] = "broadcast_text"
            await query.message.edit_text("📢 Broadcast uchun matn yozing:")
            return
        
        elif action == "qo'shish":
            context.user_data["action"] = "add_channel"
            await query.message.edit_text("➕ Kanal nomini yozing (masalan @kanal_nomi):")
            return
        
        elif action == "tekshirish":
            channels = fetch_all("SELECT channel FROM channels")
            if channels:
                text = "📺 Majburiy kanallar:\n\n"
                for i, c in enumerate(channels, 1):
                    text += f"{i}. {c[0]}\n"
                await query.message.edit_text(text)
            else:
                await query.message.edit_text("📭 Hali kanal qo'shilmagan.")
            return
        
        elif action == "o'chirish":
            context.user_data["action"] = "delete_channel"
            await query.message.edit_text("🗑 O'chiriladigan kanal nomini yozing:")
            return
        
        elif action == "matn":
            if "video_caption" in data:
                context.user_data["action"] = "add_video_caption"
                await query.message.edit_text("📝 Video ostidagi matnni yozing:")
            elif "start_message" in data:
                context.user_data["action"] = "add_start_message"
                await query.message.edit_text("🔤 Startdagi xabar matnini yozing:")
            elif "premium_text" in data:
                context.user_data["action"] = "add_premium_text"
                await query.message.edit_text("⭐ Premium matnni yozing:")
            return
        
        elif action == "ko'rish":
            if "video_caption" in data:
                result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
                if result:
                    await query.message.edit_text(f"📝 Video ostidagi matn:\n\n{result[0]}")
                else:
                    await query.message.edit_text("📭 Hali video ostidagi matn qo'shilmagan.")
            elif "start_message" in data:
                result = fetch_one("SELECT message_text FROM start_messages ORDER BY id DESC LIMIT 1")
                if result:
                    await query.message.edit_text(f"🔤 Startdagi xabar:\n\n{result[0]}")
                else:
                    await query.message.edit_text("📭 Hali start xabari qo'shilmagan.")
            elif "premium_text" in data:
                result = fetch_one("SELECT text, photo_id, caption FROM premium_texts ORDER BY id DESC LIMIT 1")
                if result:
                    text, photo_id, caption = result
                    if photo_id:
                        await query.message.edit_text(f"⭐ Premium matn (rasm bilan):\n\n{caption}")
                    else:
                        await query.message.edit_text(f"⭐ Premium matn:\n\n{text}")
                else:
                    await query.message.edit_text("📭 Hali premium matn qo'shilmagan.")
            return
        
        elif action == "r\n🖼️":
            context.user_data["action"] = "add_premium_photo"
            await query.message.edit_text("⭐ Premium matn uchun rasm yuboring:")
            return
        
        elif action == "o'chirish":
            if "video_caption" in data:
                execute_query("DELETE FROM video_captions")
                await query.message.edit_text("✅ Video ostidagi matn o'chirildi!")
            elif "start_message" in data:
                execute_query("DELETE FROM start_messages")
                await query.message.edit_text("✅ Startdagi xabar o'chirildi!")
            elif "premium_text" in data:
                execute_query("DELETE FROM premium_texts")
                await query.message.edit_text("✅ Premium matn o'chirildi!")
            return
        
        elif action == "userga":
            context.user_data["action"] = "give_premium_user"
            await query.message.edit_text("👤 Premium beriladigan user ID ni kiriting:")
            return
        
        elif action == "foydalanuvchilar":
            premium_users = fetch_all("SELECT pu.user_id, pu.expiry_date FROM premium_users pu WHERE pu.expiry_date > CURRENT_TIMESTAMP")
            
            if not premium_users:
                await query.message.edit_text("📭 Hozircha premium foydalanuvchilar yo'q.")
                return
            
            text = "🎫 Premium foydalanuvchilar:\n\n"
            for i, user in enumerate(premium_users, 1):
                user_id, expiry_date = user
                if isinstance(expiry_date, datetime):
                    days_left = (expiry_date - datetime.now()).days
                    expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M')
                else:
                    expiry_dt = datetime.fromisoformat(expiry_date)
                    days_left = (expiry_dt - datetime.now()).days
                    expiry_str = expiry_date
                
                text += f"{i}. User ID: {user_id}\nMuddati: {expiry_str}\nQolgan kun: {days_left}\n\n"
            
            await query.message.edit_text(text)
            return
        
        elif action == "premiumni":
            context.user_data["action"] = "remove_premium_user"
            await query.message.edit_text("🗑 Premium olib tashlanadigan user ID ni kiriting:")
            return
    
    # ---------- VIDEO EDIT TUGMALARI ----------
    elif data.startswith("update_"):
        short_code = data.split("_")[1]
        code = get_original_code_from_callback(short_code)
        
        context.user_data.clear()
        context.user_data["action"] = "update_code"
        context.user_data["old_code"] = code
        await query.message.reply_text(f"Yangi kodni yozing (eski kod: {code}):")
        return
    
    elif data.startswith("delete_"):
        short_code = data.split("_")[1]
        code = get_original_code_from_callback(short_code)
        
        execute_query("DELETE FROM video_stats WHERE code=%s" if DATABASE_URL else "DELETE FROM video_stats WHERE code=?", (code,))
        execute_query("DELETE FROM films WHERE code=%s" if DATABASE_URL else "DELETE FROM films WHERE code=?", (code,))
        
        update_total_videos_count()
        
        await query.message.reply_text(f"✅ Video {code} o'chirildi!")
        return
    
    elif data.startswith("edit_caption_"):
        short_code = data.replace("edit_caption_", "")
        code = get_original_code_from_callback(short_code)
        
        context.user_data.clear()
        context.user_data["action"] = "edit_video_caption"
        context.user_data["video_code"] = code
        context.user_data["video_type"] = "normal"
        
        result = fetch_one("SELECT caption FROM films WHERE code=%s" if DATABASE_URL else "SELECT caption FROM films WHERE code=?", (code,))
        current_caption = result[0] if result else ""
        
        await query.message.reply_text(f"📝 Video uchun yangi caption yozing (hozirgi: {current_caption}):")
        return
    
    # ---------- PREMIUM VIDEO EDIT TUGMALARI ----------
    elif data.startswith("premium_update_"):
        short_code = data.replace("premium_update_", "")
        code = get_original_code_from_callback(short_code)
        
        context.user_data.clear()
        context.user_data["action"] = "update_premium_code"
        context.user_data["old_code"] = code
        await query.message.reply_text(f"🎬 Premium video uchun yangi kod yozing (eski kod: {code}):")
        return
    
    elif data.startswith("premium_delete_"):
        short_code = data.replace("premium_delete_", "")
        code = get_original_code_from_callback(short_code)
        
        execute_query("DELETE FROM video_stats WHERE code=%s" if DATABASE_URL else "DELETE FROM video_stats WHERE code=?", (code,))
        execute_query("DELETE FROM premium_videos WHERE code=%s" if DATABASE_URL else "DELETE FROM premium_videos WHERE code=?", (code,))
        
        update_total_videos_count()
        
        await query.message.reply_text(f"✅ Premium video {code} o'chirildi!")
        return
    
    elif data.startswith("premium_edit_caption_"):
        short_code = data.replace("premium_edit_caption_", "")
        code = get_original_code_from_callback(short_code)
        
        context.user_data.clear()
        context.user_data["action"] = "edit_video_caption"
        context.user_data["video_code"] = code
        context.user_data["video_type"] = "premium"
        
        result = fetch_one("SELECT caption FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT caption FROM premium_videos WHERE code=?", (code,))
        current_caption = result[0] if result else ""
        
        await query.message.reply_text(f"📝 Premium video uchun yangi caption yozing (hozirgi: {current_caption}):")
        return

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return
    if not update.message.video:
        return
    
    action = context.user_data.get("action")
    
    if action == "broadcast":
        context.user_data["broadcast_video"] = update.message.video.file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("Video qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return
    
    if action == "broadcast_video":
        context.user_data["broadcast_video"] = update.message.video.file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast_video"
        await update.message.reply_text("✅ Video qabul qilindi! Broadcastni boshlash uchun 'HA' yozing:")
        return
    
    if action == "upload_premium_video":
        video_caption = update.message.caption or ""
        context.user_data["premium_video_file_id"] = update.message.video.file_id
        context.user_data["premium_video_caption"] = video_caption
        context.user_data["action"] = "set_premium_code"
        await update.message.reply_text("🎬 Premium video qabul qilindi! Endi video uchun kod yoki linkni yozing:")
        return
    
    # BOSHQA HOLATLAR: Yangi video yuklash
    video_caption = update.message.caption or ""
    context.user_data.clear()
    context.user_data["video_file_id"] = update.message.video.file_id
    context.user_data["video_caption"] = video_caption
    context.user_data["action"] = "set_code"
    await update.message.reply_text("📤 Video qabul qilindi! Endi video uchun kod yoki Instagram linkini yozing:")
    return

# ---------- OWNER PHOTO HANDLER ----------
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
    
    if action == "broadcast_photo":
        context.user_data["broadcast_photo"] = update.message.photo[-1].file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast_photo"
        await update.message.reply_text("✅ Rasm qabul qilindi! Broadcastni boshlash uchun 'HA' yozing:")
        return
    
    if action == "add_premium_photo":
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        execute_query("INSERT INTO premium_texts (photo_id, caption) VALUES (%s, %s)" if DATABASE_URL else "INSERT INTO premium_texts (photo_id, caption) VALUES (?, ?)", (photo_id, caption))
        await update.message.reply_text("✅ Premium rasm matni saqlandi!")
        context.user_data.clear()

# ---------- PHOTO HANDLER ----------
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
    if user_id == OWNER_ID:
        # Video ostidagi matn qo'shish
        if action == "add_video_caption":
            execute_query("INSERT INTO video_captions (caption_text) VALUES (%s)" if DATABASE_URL else "INSERT INTO video_captions (caption_text) VALUES (?)", (text,))
            await update.message.reply_text("✅ Video ostidagi matn saqlandi! Endi barcha videolardan keyin bu matn chiqadi.")
            context.user_data.clear()
            return
        
        # Start xabarini qo'shish
        if action == "add_start_message":
            execute_query("INSERT INTO start_messages (message_text) VALUES (%s)" if DATABASE_URL else "INSERT INTO start_messages (message_text) VALUES (?)", (text,))
            await update.message.reply_text("✅ Startdagi xabar saqlandi!")
            context.user_data.clear()
            return
        
        # Premium matn qo'shish
        if action == "add_premium_text":
            execute_query("INSERT INTO premium_texts (text) VALUES (%s)" if DATABASE_URL else "INSERT INTO premium_texts (text) VALUES (?)", (text,))
            await update.message.reply_text("✅ Premium matn saqlandi!")
            context.user_data.clear()
            return
        
        # Video kodi qo'shish
        if action == "set_code":
            file_id = context.user_data.get("video_file_id")
            video_caption = context.user_data.get("video_caption", "")
            
            if not file_id:
                await update.message.reply_text("Xatolik! Avval video yuboring.")
                context.user_data.clear()
                return
            
            original_text = text
            if 'instagram.com' in text.lower():
                text = clean_instagram_url(text)
                print(f"Owner tozalangan link: {text} (asl: {original_text})")
            
            existing = fetch_one("SELECT * FROM films WHERE code=%s" if DATABASE_URL else "SELECT * FROM films WHERE code=?", (text,))
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod/link band! Boshqa kod yoki link kiriting:")
                return
            
            if DATABASE_URL:
                execute_query("INSERT INTO films (code, file_id, caption) VALUES (%s, %s, %s) ON CONFLICT (code) DO UPDATE SET file_id = EXCLUDED.file_id, caption = EXCLUDED.caption", 
                             (text, file_id, video_caption))
            else:
                execute_query("INSERT OR REPLACE INTO films (code, file_id, caption) VALUES (?, ?, ?)", 
                             (text, file_id, video_caption))
            
            update_total_videos_count()
            
            if video_caption:
                caption_text = f"{video_caption}\n\n👁️ Ko'rishlar: 0"
            else:
                if text.startswith('http'):
                    caption_text = f"🔗 Link: {text}\n\n👁️ Ko'rishlar: 0"
                else:
                    caption_text = f"📹 Kod: {text}\n\n👁️ Ko'rishlar: 0"
            
            safe_code = create_safe_callback_data(text)
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                 InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"delete_{safe_code}")],
                [InlineKeyboardButton("📝 Caption edit", callback_data=f"edit_caption_{safe_code}")]
            ]
            
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            await update.message.reply_text(f"✅ Video saqlandi! {'Link' if text.startswith('http') else 'Kod'}: {text}")
            
            context.user_data.clear()
            context.user_data["action"] = "upload_video"
            return
        
        # Video qidirish
        if action == "search_video":
            original_text = text
            if 'instagram.com' in text.lower():
                text = clean_instagram_url(text)
                print(f"Owner search tozalangan link: {text} (asl: {original_text})")
            
            result = fetch_one("SELECT file_id, caption, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM films WHERE code=?", (text,))
            if result:
                file_id, video_caption, extra_text = result
                video_views = get_video_stats(text)
                
                if video_caption:
                    if "👁️ Ko'rishlar:" not in video_caption:
                        caption_text = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_text = video_caption
                else:
                    if text.startswith('http'):
                        caption_text = f"🔗 Link: {text}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_text = f"📹 Kod: {text}\n\n👁️ Ko'rishlar: {video_views}"
                
                safe_code = create_safe_callback_data(text)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                     InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"delete_{safe_code}")],
                    [InlineKeyboardButton("📝 Caption edit", callback_data=f"edit_caption_{safe_code}")]
                ]
                
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            else:
                await update.message.reply_text("Bunday kod/linkka film topilmadi!")
            context.user_data.clear()
            return
        
        # Premium video kodi qo'shish
        if action == "set_premium_code":
            file_id = context.user_data.get("premium_video_file_id")
            video_caption = context.user_data.get("premium_video_caption", "")
            
            if 'instagram.com' in text.lower():
                text = clean_instagram_url(text)
            
            existing = fetch_one("SELECT * FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT * FROM premium_videos WHERE code=?", (text,))
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod/link band! Boshqa kod yoki link kiriting:")
                return
            
            if DATABASE_URL:
                execute_query("INSERT INTO premium_videos (code, file_id, caption) VALUES (%s, %s, %s)", 
                             (text, file_id, video_caption))
            else:
                execute_query("INSERT INTO premium_videos (code, file_id, caption) VALUES (?, ?, ?)", 
                             (text, file_id, video_caption))
            
            update_total_videos_count()
            
            if video_caption:
                caption_text = f"{video_caption}\n\n👁️ Ko'rishlar: 0"
            else:
                caption_text = f"🎬 Premium video\n📹 Kod: {text}\n\n👁️ Ko'rishlar: 0"
            
            safe_code = create_safe_callback_data(text)
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"premium_update_{safe_code}"),
                 InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"premium_delete_{safe_code}")],
                [InlineKeyboardButton("📝 Caption edit", callback_data=f"premium_edit_caption_{safe_code}")]
            ]
            
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            await update.message.reply_text(f"✅ Premium video saqlandi! Kod: {text}")
            context.user_data.clear()
            return
        
        # Premium video qidirish
        if action == "search_premium_video":
            if 'instagram.com' in text.lower():
                text = clean_instagram_url(text)
            
            result = fetch_one("SELECT file_id, caption, extra_text FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM premium_videos WHERE code=?", (text,))
            if result:
                file_id, video_caption, extra_text = result
                video_views = get_video_stats(text)
                
                if video_caption:
                    if "👁️ Ko'rishlar:" not in video_caption:
                        caption_text = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_text = video_caption
                else:
                    caption_text = f"🎬 Premium video\n📹 Kod: {text}\n\n👁️ Ko'rishlar: {video_views}"
                
                safe_code = create_safe_callback_data(text)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"premium_update_{safe_code}"),
                     InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"premium_delete_{safe_code}")],
                    [InlineKeyboardButton("📝 Caption edit", callback_data=f"premium_edit_caption_{safe_code}")]
                ]
                
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            else:
                await update.message.reply_text("Bunday kod/linkka premium video topilmadi!")
            context.user_data.clear()
            return
        
        # Kanal qo'shish
        if action == "add_channel":
            if DATABASE_URL:
                execute_query("INSERT INTO channels (channel) VALUES (%s) ON CONFLICT (channel) DO NOTHING", (text,))
            else:
                execute_query("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (text,))
            await update.message.reply_text(f"Kanal qo'shildi: {text}")
            context.user_data.clear()
            return
        
        # Kanal o'chirish
        if action == "delete_channel":
            execute_query("DELETE FROM channels WHERE channel=%s" if DATABASE_URL else "DELETE FROM channels WHERE channel=?", (text,))
            await update.message.reply_text(f"Kanal o'chirildi: {text}")
            context.user_data.clear()
            return
        
        # Broadcast tasdiqlash
        if action == "confirm_broadcast":
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
        
        if action == "confirm_broadcast_photo":
            if text.upper() == "HA":
                photo_id = context.user_data.get("broadcast_photo")
                caption = context.user_data.get("broadcast_caption", "")
                users = fetch_all("SELECT user_id FROM users")
                count = 0
                failed = 0
                
                for u in users:
                    try:
                        await context.bot.send_photo(u[0], photo_id, caption=caption)
                        count += 1
                    except:
                        failed += 1
                
                await update.message.reply_text(f"✅ Broadcast {count} foydalanuvchiga yuborildi! ❌ {failed} ta yuborilmadi.")
            else:
                await update.message.reply_text("❌ Broadcast bekor qilindi.")
            context.user_data.clear()
            return
        
        if action == "confirm_broadcast_video":
            if text.upper() == "HA":
                video_id = context.user_data.get("broadcast_video")
                caption = context.user_data.get("broadcast_caption", "")
                users = fetch_all("SELECT user_id FROM users")
                count = 0
                failed = 0
                
                for u in users:
                    try:
                        await context.bot.send_video(u[0], video_id, caption=caption)
                        count += 1
                    except:
                        failed += 1
                
                await update.message.reply_text(f"✅ Broadcast {count} foydalanuvchiga yuborildi! ❌ {failed} ta yuborilmadi.")
            else:
                await update.message.reply_text("❌ Broadcast bekor qilindi.")
            context.user_data.clear()
            return
        
        # Oddiy broadcast (faqat matn)
        if action == "broadcast_text":
            users = fetch_all("SELECT user_id FROM users")
            count = 0
            failed = 0
            
            premium_result = fetch_one("SELECT text, photo_id, caption FROM premium_texts ORDER BY id DESC LIMIT 1")
            
            for u in users:
                try:
                    if premium_result:
                        premium_text, photo_id, caption = premium_result
                        if photo_id:
                            await context.bot.send_photo(u[0], photo_id, caption=caption)
                        elif premium_text:
                            await context.bot.send_message(u[0], premium_text)
                    await context.bot.send_message(u[0], text)
                    count += 1
                except:
                    failed += 1
            
            await update.message.reply_text(f"✅ Broadcast {count} foydalanuvchiga yuborildi! ❌ {failed} ta yuborilmadi.")
            context.user_data.clear()
            return
        
        # Owner kodi alishtirish
        if action == "update_code":
            new_code = text
            old_code = context.user_data.get("old_code")
            
            if 'instagram.com' in new_code.lower():
                new_code = clean_instagram_url(new_code)
                print(f"Owner update tozalangan link: {new_code}")
            
            existing = fetch_one("SELECT * FROM films WHERE code=%s AND code != %s" if DATABASE_URL else "SELECT * FROM films WHERE code=? AND code!=?", (new_code, old_code))
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod band! Boshqa kod kiriting:")
                return
            
            execute_query("UPDATE films SET code=%s WHERE code=%s" if DATABASE_URL else "UPDATE films SET code=? WHERE code=?", (new_code, old_code))
            execute_query("UPDATE video_stats SET code=%s WHERE code=%s" if DATABASE_URL else "UPDATE video_stats SET code=? WHERE code=?", (new_code, old_code))
            
            result = fetch_one("SELECT file_id, caption, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM films WHERE code=?", (new_code,))
            if result:
                file_id, video_caption, extra_text = result
                video_views = get_video_stats(new_code)
                
                if video_caption:
                    if "👁️ Ko'rishlar:" not in video_caption:
                        caption_text = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_text = video_caption
                else:
                    if new_code.startswith('http'):
                        caption_text = f"🔗 Link: {new_code}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_text = f"📹 Kod: {new_code}\n\n👁️ Ko'rishlar: {video_views}"
                
                safe_code = create_safe_callback_data(new_code)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                     InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"delete_{safe_code}")],
                    [InlineKeyboardButton("📝 Caption edit", callback_data=f"edit_caption_{safe_code}")]
                ]
                
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            await update.message.reply_text(f"Video kodi yangilandi! Yangi kod: {new_code}")
            context.user_data.clear()
            return
        
        # Premium video kod alishtirish
        elif action == "update_premium_code":
            new_code = text
            old_code = context.user_data.get("old_code")
            
            if 'instagram.com' in new_code.lower():
                new_code = clean_instagram_url(new_code)
            
            existing = fetch_one("SELECT * FROM premium_videos WHERE code=%s AND code != %s" if DATABASE_URL else "SELECT * FROM premium_videos WHERE code=? AND code!=?", (new_code, old_code))
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod band! Boshqa kod kiriting:")
                return
            
            execute_query("UPDATE premium_videos SET code=%s WHERE code=%s" if DATABASE_URL else "UPDATE premium_videos SET code=? WHERE code=?", (new_code, old_code))
            execute_query("UPDATE video_stats SET code=%s WHERE code=%s" if DATABASE_URL else "UPDATE video_stats SET code=? WHERE code=?", (new_code, old_code))
            
            result = fetch_one("SELECT file_id, caption, extra_text FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM premium_videos WHERE code=?", (new_code,))
            if result:
                file_id, video_caption, extra_text = result
                video_views = get_video_stats(new_code)
                
                if video_caption:
                    if "👁️ Ko'rishlar:" not in video_caption:
                        caption_text = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
                    else:
                        caption_text = video_caption
                else:
                    caption_text = f"🎬 Premium video\n📹 Kod: {new_code}\n\n👁️ Ko'rishlar: {video_views}"
                
                safe_code = create_safe_callback_data(new_code)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"premium_update_{safe_code}"),
                     InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"premium_delete_{safe_code}")],
                    [InlineKeyboardButton("📝 Caption edit", callback_data=f"premium_edit_caption_{safe_code}")]
                ]
                
                await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_text)
            
            await update.message.reply_text(f"✅ Premium video kodi yangilandi! Yangi kod: {new_code}")
            context.user_data.clear()
            return
        
        # Caption edit
        if action == "edit_video_caption":
            new_caption = text
            video_code = context.user_data.get("video_code")
            video_type = context.user_data.get("video_type")
            
            video_views = get_video_stats(video_code)
            
            if new_caption:
                caption_with_stats = f"{new_caption}\n\n👁️ Ko'rishlar: {video_views}"
            else:
                if video_code.startswith('http'):
                    caption_with_stats = f"🔗 Link: {video_code}\n\n👁️ Ko'rishlar: {video_views}"
                else:
                    caption_with_stats = f"📹 Kod: {video_code}\n\n👁️ Ko'rishlar: {video_views}"
            
            if video_type == "normal":
                execute_query("UPDATE films SET caption=%s WHERE code=%s" if DATABASE_URL else "UPDATE films SET caption=? WHERE code=?", (caption_with_stats, video_code))
                
                result = fetch_one("SELECT file_id, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code=?", (video_code,))
                if result:
                    file_id, extra_text = result
                    
                    safe_code = create_safe_callback_data(video_code)
                    keyboard = [
                        [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                         InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"delete_{safe_code}")],
                        [InlineKeyboardButton("📝 Caption edit", callback_data=f"edit_caption_{safe_code}")]
                    ]
                    
                    await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_with_stats)
            
            elif video_type == "premium":
                execute_query("UPDATE premium_videos SET caption=%s WHERE code=%s" if DATABASE_URL else "UPDATE premium_videos SET caption=? WHERE code=?", (caption_with_stats, video_code))
                
                result = fetch_one("SELECT file_id, extra_text FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT file_id, extra_text FROM premium_videos WHERE code=?", (video_code,))
                if result:
                    file_id, extra_text = result
                    
                    safe_code = create_safe_callback_data(video_code)
                    keyboard = [
                        [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"premium_update_{safe_code}"),
                         InlineKeyboardButton("🗑️ Videoni o'chirish", callback_data=f"premium_delete_{safe_code}")],
                        [InlineKeyboardButton("📝 Caption edit", callback_data=f"premium_edit_caption_{safe_code}")]
                    ]
                    
                    await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=caption_with_stats)
            
            await update.message.reply_text("✅ Video caption yangilandi!")
            context.user_data.clear()
            return
        
        # Userga premium berish
        elif action == "give_premium_user":
            try:
                target_user_id = int(text)
                context.user_data["action"] = "set_premium_days_direct"
                context.user_data["target_user"] = target_user_id
                await update.message.reply_text(f"User {target_user_id} uchun premium kunlar sonini kiriting:")
            except ValueError:
                await update.message.reply_text("Iltimos, to'g'ri user ID kiriting.")
            return
        
        # Premium kunlarini belgilash
        elif action == "set_premium_days_direct":
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
            try:
                target_user_id = int(text)
                execute_query("DELETE FROM premium_users WHERE user_id=%s" if DATABASE_URL else "DELETE FROM premium_users WHERE user_id=?", (target_user_id,))
                await update.message.reply_text(f"✅ User {target_user_id} ning premiumi olib tashlandi!")
            except ValueError:
                await update.message.reply_text("Iltimos, to'g'ri user ID kiriting.")
            context.user_data.clear()
            return
    
    # ---------- FOYDALANUVCHI KINO KO'RISH ----------
    original_user_text = text
    if 'instagram.com' in text.lower():
        text = clean_instagram_url(text)
        print(f"User tozalangan link: {text} (asl: {original_user_text})")
    
    # Premium video tekshirish
    premium_result = fetch_one("SELECT file_id, caption, extra_text FROM premium_videos WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM premium_videos WHERE code=?", (text,))
    
    if premium_result:
        file_id, video_caption, extra_text = premium_result
        is_premium = is_premium_user(user_id)
        
        if is_premium:
            context.user_data["last_video_code"] = text
            update_video_stats(text)
            video_views = get_video_stats(text)
            
            if video_caption:
                caption_with_stats = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
            else:
                caption_with_stats = f"🎬 Premium video\n📹 Kod: {text}\n\n👁️ Ko'rishlar: {video_views}"
            
            await update.message.reply_video(file_id, caption=caption_with_stats)
            await send_video_caption(update, context)
            return
        else:
            premium_text_result = fetch_one("SELECT text, photo_id, caption FROM premium_texts ORDER BY id DESC LIMIT 1")
            if premium_text_result:
                premium_text, photo_id, caption = premium_text_result
                if photo_id:
                    await update.message.reply_photo(photo_id, caption=caption)
                elif premium_text:
                    await update.message.reply_text(premium_text)
            
            await update.message.reply_text(
                "❗ Bu video faqat premium foydalanuvchilar uchun!\n"
                "Premium olish uchun admin bilan bog'laning."
            )
            return
    
    # Oddiy video tekshirish
    result = fetch_one("SELECT file_id, caption, extra_text FROM films WHERE code=%s" if DATABASE_URL else "SELECT file_id, caption, extra_text FROM films WHERE code=?", (text,))
    
    if result:
        file_id, video_caption, extra_text = result
        context.user_data["last_video_code"] = text
        update_video_stats(text)
        video_views = get_video_stats(text)
        
        is_premium = is_premium_user(user_id)
        
        if video_caption:
            caption_with_stats = f"{video_caption}\n\n👁️ Ko'rishlar: {video_views}"
        else:
            if text.startswith('http'):
                caption_with_stats = f"🔗 Link: {text}\n\n👁️ Ko'rishlar: {video_views}"
            else:
                caption_with_stats = f"📹 Kod: {text}\n\n👁️ Ko'rishlar: {video_views}"
        
        if is_premium:
            await update.message.reply_video(file_id, caption=caption_with_stats)
            await send_video_caption(update, context)
            return
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
                
                safe_code = create_safe_callback_data(text)
                keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{safe_code}")])
                keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
                
                await update.message.reply_text(
                    "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_video(file_id, caption=caption_with_stats)
                await send_video_caption(update, context)
    else:
        await update.message.reply_text("Bunday kod/linkka film topilmadi! Iltimos, to'g'ri kod yoki linkni yuboring.")

# ---------- COMMAND HANDLER ----------
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
                INSERT OR REPLACE INTO premium_videos (user_id, expiry_date, approved_by, approved_date) 
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
app.add_handler(InlineQueryHandler(handle_inline_query))
app.add_handler(ChosenInlineResultHandler(handle_chosen_inline_result))

# ---------- BOT ISHGA TUSHGANDA ----------
if __name__ == '__main__':
    print("Bot ishga tushdi...")
    
    # Barcha videolar sonini hisoblash
    update_total_videos_count()
    
    # Mavjud videolarni yangi formatga o'tkazish
    films = fetch_all("SELECT code, caption FROM films")
    for film in films:
        code, current_caption = film
        
        video_views = get_video_stats(code)
        
        if current_caption and "👁️ Ko'rishlar:" not in current_caption:
            new_caption = f"{current_caption}\n\n👁️ Ko'rishlar: {video_views}"
            execute_query("UPDATE films SET caption=%s WHERE code=%s" if DATABASE_URL else "UPDATE films SET caption=? WHERE code=?", (new_caption, code))
        elif not current_caption:
            if code.startswith('http'):
                new_caption = f"🔗 Link: {code}\n\n👁️ Ko'rishlar: {video_views}"
            else:
                new_caption = f"📹 Kod: {code}\n\n👁️ Ko'rishlar: {video_views}"
            execute_query("UPDATE films SET caption=%s WHERE code=%s" if DATABASE_URL else "UPDATE films SET caption=? WHERE code=?", (new_caption, code))
    
    # Premium videolarni yangi formatga o'tkazish
    premium_films = fetch_all("SELECT code, caption FROM premium_videos")
    for film in premium_films:
        code, current_caption = film
        
        video_views = get_video_stats(code)
        
        if current_caption and "👁️ Ko'rishlar:" not in current_caption:
            new_caption = f"{current_caption}\n\n👁️ Ko'rishlar: {video_views}"
            execute_query("UPDATE premium_videos SET caption=%s WHERE code=%s" if DATABASE_URL else "UPDATE premium_videos SET caption=? WHERE code=?", (new_caption, code))
        elif not current_caption:
            new_caption = f"🎬 Premium video\n📹 Kod: {code}\n\n👁️ Ko'rishlar: {video_views}"
            execute_query("UPDATE premium_videos SET caption=%s WHERE code=%s" if DATABASE_URL else "UPDATE premium_videos SET caption=? WHERE code=?", (new_caption, code))
    
    app.run_polling()

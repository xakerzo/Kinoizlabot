from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, InlineQueryHandler, ChosenInlineResultHandler
import urllib.parse
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timedelta
import hashlib
import re
import logging
import sys

# ---------- LOGGING ----------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ---------- KONFIGURATSIYA ----------
OWNER_ID = 1373647  # O'z Telegram ID'ingizni qo'ying
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN muhit o'zgaruvchisi topilmadi!")
    sys.exit(1)

BOT_USERNAME = "@kinoni_izlabot"
BOT_LINK = "https://t.me/kinoni_izlabot"
DATABASE_URL = os.environ.get('DATABASE_URL')

# ---------- DATABASE FUNKSIYALARI ----------
def get_db_connection_and_cursor():
    """Database ulanishi va cursor olish"""
    if DATABASE_URL:
        # PostgreSQL
        try:
            result = urlparse(DATABASE_URL)
            conn = psycopg2.connect(
                database=result.path[1:] if result.path else 'postgres',
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                sslmode='require'
            )
            cursor = conn.cursor()
            return conn, cursor, 'postgres'
        except Exception as e:
            logger.error(f"PostgreSQL ulanish xatosi: {e}")
            raise
    else:
        # SQLite (local development)
        import sqlite3
        conn = sqlite3.connect("kino_bot.db", check_same_thread=False)
        cursor = conn.cursor()
        return conn, cursor, 'sqlite'

def close_db_connection(conn, cursor):
    """Database ulanishini yopish"""
    try:
        cursor.close()
        conn.close()
    except:
        pass

def init_database():
    """Database jadvallarini yaratish/yangilash"""
    conn, cursor, db_type = get_db_connection_and_cursor()
    
    try:
        # films jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS films (
                    code TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    extra_text TEXT DEFAULT '',
                    is_premium BOOLEAN DEFAULT FALSE,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS films (
                    code TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    extra_text TEXT DEFAULT '',
                    is_premium BOOLEAN DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # users jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # channels jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel TEXT PRIMARY KEY
            )
        """)
        
        # partners jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS partners (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS partners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL
                )
            """)
        
        # premium_users jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premium_users (
                    user_id BIGINT PRIMARY KEY,
                    expiry_date TIMESTAMP,
                    approved_by BIGINT,
                    approved_date TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premium_users (
                    user_id INTEGER PRIMARY KEY,
                    expiry_date TIMESTAMP,
                    approved_by INTEGER,
                    approved_date TIMESTAMP
                )
            """)
        
        # bypass_requests jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bypass_requests (
                    user_id BIGINT PRIMARY KEY,
                    request_text TEXT,
                    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bypass_requests (
                    user_id INTEGER PRIMARY KEY,
                    request_text TEXT,
                    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
        
        # ad_texts jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ad_texts (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ad_texts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL
                )
            """)
        
        # video_captions jadvali
        if db_type == 'postgres':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_captions (
                    id SERIAL PRIMARY KEY,
                    caption_text TEXT NOT NULL
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_captions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caption_text TEXT NOT NULL
                )
            """)
        
        conn.commit()
        logger.info("✅ Database jadvallari yaratildi/tekshirildi")
        
    except Exception as e:
        logger.error(f"Database yaratishda xatolik: {e}")
        conn.rollback()
        raise
    finally:
        close_db_connection(conn, cursor)

def execute_query(query, params=None):
    """Query bajarish"""
    conn, cursor, db_type = get_db_connection_and_cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logger.error(f"Query bajarishda xatolik: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        conn.rollback()
        raise
    finally:
        close_db_connection(conn, cursor)

def fetch_one(query, params=None):
    """Bitta natija olish"""
    conn, cursor, db_type = get_db_connection_and_cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchone()
        return result
    except Exception as e:
        logger.error(f"Fetch one xatolik: {e}")
        logger.error(f"Query: {query}")
        return None
    finally:
        close_db_connection(conn, cursor)

def fetch_all(query, params=None):
    """Barcha natijalarni olish"""
    conn, cursor, db_type = get_db_connection_and_cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Exception as e:
        logger.error(f"Fetch all xatolik: {e}")
        logger.error(f"Query: {query}")
        return []
    finally:
        close_db_connection(conn, cursor)

# ---------- YORDAMCHI FUNKSIYALAR ----------
def clean_instagram_url(url):
    """Instagram linkini to'g'ri shaklga keltirish"""
    if not url or 'instagram.com' not in url.lower():
        return url
    
    # Patternni kengaytirish
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:reel|p|tv|stories)/([A-Za-z0-9_-]+)/?)'
    
    match = re.search(pattern, url)
    if match:
        clean_url = match.group(1)
        if clean_url.endswith('/'):
            clean_url = clean_url[:-1]
        return clean_url
    
    return url

def is_premium_user(user_id):
    """Foydalanuvchi premium ekanligini tekshirish"""
    result = fetch_one("SELECT expiry_date FROM premium_users WHERE user_id = %s" if DATABASE_URL else "SELECT expiry_date FROM premium_users WHERE user_id = ?", (user_id,))
    
    if not result:
        return False
    
    expiry_date = result[0]
    
    if expiry_date:
        if isinstance(expiry_date, datetime):
            return expiry_date > datetime.now()
        else:
            try:
                return datetime.fromisoformat(str(expiry_date)) > datetime.now()
            except:
                return False
    return False

def increment_video_views(code):
    """Video ko'rishlar sonini oshirish"""
    try:
        execute_query("UPDATE films SET views = views + 1 WHERE code = %s" if DATABASE_URL else "UPDATE films SET views = views + 1 WHERE code = ?", (code,))
    except Exception as e:
        logger.error(f"Ko'rishlar sonini oshirishda xatolik: {e}")

def create_safe_callback_data(code):
    """Callback data uchun xavfsiz kod yaratish"""
    if len(code) > 50:
        hash_object = hashlib.md5(code.encode())
        short_code = hash_object.hexdigest()[:10]
    else:
        short_code = code
    return short_code

def get_original_code_from_callback(short_code):
    """Callback datadan asl kodni olish"""
    films = fetch_all("SELECT code FROM films")
    for film in films:
        original_code = film[0]
        if create_safe_callback_data(original_code) == short_code:
            return original_code
    return short_code

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    try:
        user_id = update.message.from_user.id
        args = context.args
        
        logger.info(f"Start command: user_id={user_id}, args={args}")
        
        # Foydalanuvchini database ga qo'shish
        try:
            if DATABASE_URL:
                execute_query(
                    "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                    (user_id,)
                )
            else:
                execute_query(
                    "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                    (user_id,)
                )
        except Exception as e:
            logger.error(f"User qo'shishda xatolik: {e}")
        
        # Agar argument bo'lsa (video kodi yoki link)
        if args and len(args) > 0:
            video_code = urllib.parse.unquote(args[0])
            
            # Instagram linkini tozalash
            if 'instagram.com' in video_code.lower():
                video_code = clean_instagram_url(video_code)
            
            result = fetch_one(
                "SELECT file_id, extra_text, is_premium FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text, is_premium FROM films WHERE code = ?",
                (video_code,)
            )
            
            if result:
                file_id, extra_text, is_premium_video = result
                
                # Premium video tekshirish
                if is_premium_video and not is_premium_user(user_id):
                    await update.message.reply_text(
                        "❌ Bu video faqat premium foydalanuvchilar uchun!\n\n"
                        "Premium obuna sotib olish uchun admin bilan bog'laning.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🎫 Premium sotib olish", callback_data="buy_premium")]
                        ])
                    )
                    return
                
                context.user_data["last_video_code"] = video_code
                increment_video_views(video_code)
                
                # Ko'rishlar sonini olish
                view_count = fetch_one(
                    "SELECT views FROM films WHERE code = %s" if DATABASE_URL else "SELECT views FROM films WHERE code = ?",
                    (video_code,)
                )
                views = view_count[0] if view_count else 0
                
                is_premium = is_premium_user(user_id)
                
                if is_premium:
                    caption = f"Kod: {video_code}\n{extra_text}\n\n👁 Ko'rishlar: {views}\n{BOT_USERNAME}"
                    await update.message.reply_video(file_id, caption=caption)
                    await send_video_caption(update, context)
                else:
                    channels = fetch_all("SELECT channel FROM channels")
                    not_subscribed = []
                    
                    for channel in channels:
                        try:
                            member = await context.bot.get_chat_member(channel[0], user_id)
                            if member.status in ["left", "kicked"]:
                                not_subscribed.append(channel[0])
                        except Exception as e:
                            logger.error(f"Kanal a'zoligini tekshirishda xatolik: {e}")
                            not_subscribed.append(channel[0])
                    
                    if not_subscribed:
                        keyboard = []
                        for channel in not_subscribed:
                            keyboard.append([InlineKeyboardButton(f"✅ Obuna bo'lish: {channel}", url=f"https://t.me/{channel[1:]}")])
                        
                        safe_code = create_safe_callback_data(video_code)
                        keyboard.append([InlineKeyboardButton("🔄 Tekshirish", callback_data=f"check_subs_{safe_code}")])
                        keyboard.append([InlineKeyboardButton("🎫 Reklama siz ishlatish", callback_data="bypass_ads")])
                        
                        await update.message.reply_text(
                            "Iltimos, kinoni ko'rishdan oldin quyidagi kanallarga obuna bo'ling:",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    else:
                        caption = f"Kod: {video_code}\n{extra_text}\n\n👁 Ko'rishlar: {views}\n{BOT_USERNAME}"
                        await update.message.reply_video(file_id, caption=caption)
                        await send_video_caption(update, context)
                return
            else:
                await update.message.reply_text("❌ Bu kod/link bo'yicha video topilmadi!")
                # Intentional fall-through to show welcome message
        
        # Videolar sonini olish
        try:
            video_count_result = fetch_one("SELECT COUNT(*) FROM films")
            video_count = video_count_result[0] if video_count_result else 0
            video_stats_text = f"\n\n📊 Botda jami {video_count} ta video mavjud!"
        except:
            video_stats_text = "\n\n📊 Botda videolar mavjud!"
        
        # Hamkorlarni olish
        partners_texts = fetch_all("SELECT text FROM partners ORDER BY id")
        
        if partners_texts:
            partners_message = "🤝 Hamkorlarimiz:\n" + "\n".join([text[0] for text in partners_texts])
            partners_message += video_stats_text
            await update.message.reply_text(partners_message)
        else:
            await update.message.reply_text(f"Salom!{video_stats_text}")
        
        # Owner yoki oddiy foydalanuvchi uchun menu
        if user_id == OWNER_ID:
            try:
                user_count_result = fetch_one("SELECT COUNT(*) FROM users")
                user_count = user_count_result[0] if user_count_result else 0
                
                premium_video_count_result = fetch_one("SELECT COUNT(*) FROM films WHERE is_premium = TRUE")
                premium_video_count = premium_video_count_result[0] if premium_video_count_result else 0
                
                keyboard = [
                    [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video"),
                     InlineKeyboardButton("🎬 Premium video yuklash", callback_data="upload_premium_video")],
                    [InlineKeyboardButton("🔍 Video qidirish", callback_data="search_video")],
                    [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
                    [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel"),
                     InlineKeyboardButton("🗑 Kanalni o'chirish", callback_data="delete_channel")],
                    [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")],
                    [InlineKeyboardButton("📝 Qo'shimcha matn", callback_data="manage_text")],
                    [InlineKeyboardButton("🤝 Hamkorlar", callback_data="manage_partners")],
                    [InlineKeyboardButton("🎫 Reklama sozlamalari", callback_data="ad_settings")],
                    [InlineKeyboardButton("👤 Premium boshqarish", callback_data="premium_management")],
                    [InlineKeyboardButton("📝 Video ostidagi matn", callback_data="video_caption_manage")],
                    [InlineKeyboardButton(f"👥 Foydalanuvchilar: {user_count}", callback_data="user_count")],
                    [InlineKeyboardButton(f"📊 Video statistika", callback_data="video_stats")]
                ]
                
                await update.message.reply_text(
                    "👑 Salom Owner! Quyidagi menyudan tanlang:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.error(f"Owner menu yaratishda xatolik: {e}")
                await update.message.reply_text("Salom Owner! Kino kodi yoki Instagram linkini kiriting:")
        else:
            if is_premium_user(user_id):
                await update.message.reply_text(
                    f"🎉 Siz premium foydalanuvchisiz! Kanallarga obuna bo'lish shart emas.{video_stats_text}\n\n"
                    f"Kino kodi yoki Instagram linkini kiriting:"
                )
            else:
                await update.message.reply_text(
                    f"Salom!{video_stats_text}\n\n"
                    f"Kino kodi yoki Instagram linkini kiriting:"
                )
                
    except Exception as e:
        logger.error(f"Start command xatolik: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi, iltimos qayta urinib ko'ring.")

# ---------- VIDEO CAPTION FUNKSIYALARI ----------
async def send_video_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Video ostidagi matnni yuborish"""
    try:
        caption_result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        
        if caption_result and caption_result[0]:
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
        logger.error(f"Video caption yuborishda xatolik: {e}")

async def send_callback_caption(query, context: ContextTypes.DEFAULT_TYPE):
    """Callback uchun video caption yuborish"""
    try:
        caption_result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        
        if caption_result and caption_result[0]:
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
        logger.error(f"Callback caption yuborishda xatolik: {e}")

# ---------- DO'STLARGA YUBORISH FUNKSIYALARI ----------
async def start_share_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Do'stlarga yuborishni boshlash"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    last_code = context.user_data.get("last_video_code")
    
    if not last_code:
        await query.message.reply_text("❌ Video kodi topilmadi. Iltimos, avval videoni ko'ring.")
        return
    
    result = fetch_one(
        "SELECT file_id, extra_text FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text FROM films WHERE code = ?",
        (last_code,)
    )
    
    if not result:
        await query.message.reply_text("❌ Video topilmadi.")
        return
    
    await query.message.reply_text(
        f"🎬 Video ulashish\n\n"
        f"📹 Video: {last_code}\n\n"
        f"Do'stlaringizga video yuborish uchun quyidagi tugmani bosing va kontaktlaringizdan birini tanlang:"
    )
    
    await query.message.reply_text(
        "📤 Do'stingizga video yuborish uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📤 Do'stlarga yuborish", switch_inline_query="")
        ]])
    )

# ---------- INLINE QUERY HANDLER ----------
async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline query handler"""
    query = update.inline_query
    user_id = query.from_user.id
    query_text = query.query.strip()
    
    logger.info(f"Inline query: user_id={user_id}, query={query_text}")
    
    if query_text:
        # Agar query bo'lsa, videolarni qidirish
        films = fetch_all(
            "SELECT code FROM films WHERE code ILIKE %s ORDER BY code LIMIT 10" if DATABASE_URL else 
            "SELECT code FROM films WHERE code LIKE ? ORDER BY code LIMIT 10",
            (f"%{query_text}%",)
        )
    else:
        # Agar query bo'sh bo'lsa, oxirgi ko'rgan video yoki barcha videolar
        last_code = context.user_data.get("last_video_code")
        if last_code:
            films = [(last_code,)]
        else:
            films = fetch_all("SELECT code FROM films ORDER BY created_at DESC LIMIT 10")
    
    if not films:
        await query.answer([])
        return
    
    results = []
    for film in films:
        video_code = film[0]
        
        share_text = f"🎬 Do'stim sizga video yubordi!\n\n"
        share_text += f"📹 Video kod: {video_code}\n" if not video_code.startswith('http') else f"🔗 Link: {video_code}\n"
        share_text += f"🤖 Bot: {BOT_USERNAME}\n\n"
        share_text += f"Video ni ko'rish uchun quyidagi tugmani bosing 👇"
        
        keyboard = [[
            InlineKeyboardButton("🎬 Videoni ko'rish", url=f"{BOT_LINK}?start={urllib.parse.quote(video_code)}")
        ]]
        
        result_id = hashlib.md5(video_code.encode()).hexdigest()[:64]
        
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title=f"📹 Video: {video_code[:30]}{'...' if len(video_code) > 30 else ''}",
                description=f"Do'stingizga video yuboring - {video_code}",
                input_message_content=InputTextMessageContent(
                    message_text=share_text,
                    disable_web_page_preview=True
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        )
    
    await query.answer(results)

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tanlangan inline result"""
    chosen_result = update.chosen_inline_result
    user_id = chosen_result.from_user.id
    result_id = chosen_result.result_id
    
    logger.info(f"Chosen inline result: user_id={user_id}, result_id={result_id}")
    
    # Shared count ni oshirish
    context.user_data.setdefault("shared_count", 0)
    context.user_data["shared_count"] += 1
    
    try:
        await context.bot.send_message(
            user_id,
            f"✅ Video do'stingizga yuborildi!\n"
            f"Jami yuborilgan do'stlar: {context.user_data['shared_count']}"
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xatolik: {e}")

# ---------- CALLBACK HANDLER ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query handler"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Callback: user_id={user_id}, data={data}")
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Callback answer xatolik: {e}")
    
    # ---------- PREMIUM SOTIB OLISH ----------
    if data == "buy_premium":
        await query.message.reply_text(
            "🎫 Premium obuna sotib olish uchun admin bilan bog'laning:\n\n"
            "Admin: @admin_username\n\n"
            "Premium narxlar:\n"
            "• 30 kun: 10,000 so'm\n"
            "• 90 kun: 25,000 so'm\n"
            "• 365 kun: 80,000 so'm"
        )
        return
    
    # ---------- VIDEO STATISTIKA ----------
    elif data == "video_stats":
        if user_id != OWNER_ID:
            await query.message.reply_text("❌ Bu funksiya faqat admin uchun!")
            return
        
        try:
            total_videos = fetch_one("SELECT COUNT(*) FROM films")[0] or 0
            total_views = fetch_one("SELECT SUM(views) FROM films")[0] or 0
            premium_videos = fetch_one("SELECT COUNT(*) FROM films WHERE is_premium = TRUE")[0] or 0
            
            text = f"📊 Video Statistika:\n\n"
            text += f"📁 Jami videolar: {total_videos}\n"
            text += f"🎬 Premium videolar: {premium_videos}\n"
            text += f"👁 Jami ko'rishlar: {total_views}\n\n"
            
            top_videos = fetch_all("SELECT code, views FROM films ORDER BY views DESC LIMIT 10")
            if top_videos:
                text += "📈 Eng ko'p ko'rilgan videolar:\n"
                for i, video in enumerate(top_videos, 1):
                    code, views = video
                    text += f"{i}. {code[:20]}{'...' if len(code) > 20 else ''} - {views} ko'rish\n"
            
            await query.message.reply_text(text)
        except Exception as e:
            logger.error(f"Video statistika xatolik: {e}")
            await query.message.reply_text("❌ Statistika olishda xatolik!")
        return
    
    # ---------- DO'STLARGA YUBORISH ----------
    elif data == "share_friend":
        await start_share_friend(update, context)
        return
    
    # ---------- REKLAMA BYPASS ----------
    elif data == "bypass_ads":
        ad_result = fetch_one("SELECT text FROM ad_texts ORDER BY id DESC LIMIT 1")
        
        if ad_result and ad_result[0]:
            ad_text = ad_result[0]
        else:
            ad_text = "Iltimos, botdan foydalanish uchun quyidagi kanallarga obuna bo'ling yoki admin bilan bog'laning."
        
        keyboard = [[InlineKeyboardButton("📨 Chekni yuborish", callback_data="send_receipt")]]
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
    
    # ---------- OBUNA TEKSHIRISH ----------
    elif data.startswith("check_subs_"):
        short_code = data.replace("check_subs_", "")
        code = get_original_code_from_callback(short_code)
        
        result = fetch_one(
            "SELECT file_id, extra_text, is_premium FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text, is_premium FROM films WHERE code = ?",
            (code,)
        )
        
        if not result:
            await query.message.reply_text("❌ Video topilmadi!")
            return
        
        file_id, extra_text, is_premium_video = result
        
        # Premium video tekshirish
        if is_premium_video and not is_premium_user(user_id):
            await query.message.reply_text(
                "❌ Bu video faqat premium foydalanuvchilar uchun!\n\n"
                "Premium obuna sotib olish uchun admin bilan bog'laning.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎫 Premium sotib olish", callback_data="buy_premium")]
                ])
            )
            return
        
        # Kanallarga obuna tekshirish
        channels = fetch_all("SELECT channel FROM channels")
        not_subscribed = []
        
        for channel in channels:
            try:
                member = await context.bot.get_chat_member(channel[0], user_id)
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(channel[0])
            except Exception as e:
                logger.error(f"Kanal tekshirish xatolik: {e}")
                not_subscribed.append(channel[0])
        
        if not_subscribed and not is_premium_user(user_id):
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
            increment_video_views(code)
            
            view_count = fetch_one(
                "SELECT views FROM films WHERE code = %s" if DATABASE_URL else "SELECT views FROM films WHERE code = ?",
                (code,)
            )
            views = view_count[0] if view_count else 0
            
            context.user_data["last_video_code"] = code
            
            caption = f"Kod: {code}\n{extra_text}\n\n👁 Ko'rishlar: {views}\n{BOT_USERNAME}"
            await query.message.reply_video(file_id, caption=caption)
            await send_callback_caption(query, context)
        return
    
    # ---------- OWNER FUNKSIYALARI ----------
    if user_id != OWNER_ID:
        await query.message.reply_text("❌ Bu funksiya faqat admin uchun!")
        return
    
    # Video yuklash
    if data == "upload_video":
        context.user_data.clear()
        context.user_data["action"] = "upload_video"
        context.user_data["is_premium_video"] = False
        await query.message.reply_text("📤 Video yuboring:")
        return
    
    elif data == "upload_premium_video":
        context.user_data.clear()
        context.user_data["action"] = "upload_video"
        context.user_data["is_premium_video"] = True
        await query.message.reply_text("🎬 PREMIUM Video yuboring:")
        return
    
    elif data == "search_video":
        context.user_data.clear()
        context.user_data["action"] = "search_video"
        await query.message.reply_text("🔍 Qidiriladigan kod yoki linkni yozing:")
        return
    
    elif data == "broadcast":
        context.user_data.clear()
        context.user_data["action"] = "broadcast"
        await query.message.reply_text("📢 Broadcast xabar yuboring (matn, rasm, video yoki boshqa media bilan):")
        return
    
    elif data == "add_channel":
        context.user_data.clear()
        context.user_data["action"] = "add_channel"
        await query.message.reply_text("➕ Kanal nomini yozing (masalan @kanal_nomi):")
        return
    
    elif data == "delete_channel":
        context.user_data.clear()
        context.user_data["action"] = "delete_channel"
        await query.message.reply_text("🗑 O'chiriladigan kanal nomini yozing:")
        return
    
    elif data == "list_channels":
        channels = fetch_all("SELECT channel FROM channels")
        if channels:
            text = "📋 Kanallar ro'yxati:\n\n" + "\n".join([f"• {c[0]}" for c in channels])
        else:
            text = "📭 Hali kanal qo'shilmagan."
        await query.message.reply_text(text)
        return
    
    elif data == "user_count":
        user_count = fetch_one("SELECT COUNT(*) FROM users")[0] or 0
        await query.message.reply_text(f"👥 Botdagi jami foydalanuvchilar soni: {user_count}")
        return
    
    # ---------- VIDEO CAPTION MANAGEMENT ----------
    elif data == "video_caption_manage":
        keyboard = [
            [InlineKeyboardButton("➕ Matn qo'shish", callback_data="add_video_caption")],
            [InlineKeyboardButton("🔍 Matnni ko'rish", callback_data="view_video_caption")],
            [InlineKeyboardButton("🗑 Matnni o'chirish", callback_data="delete_video_caption")]
        ]
        await query.message.reply_text(
            "📝 Video ostidagi matnni boshqarish:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "add_video_caption":
        context.user_data.clear()
        context.user_data["action"] = "add_video_caption"
        await query.message.reply_text("✏️ Video dan keyin chiqadigan matnni yozing:")
        return
    
    elif data == "view_video_caption":
        result = fetch_one("SELECT caption_text FROM video_captions ORDER BY id DESC LIMIT 1")
        if result and result[0]:
            await query.message.reply_text(f"📝 Joriy video matni:\n\n{result[0]}")
        else:
            await query.message.reply_text("📭 Hali video matni qo'shilmagan.")
        return
    
    elif data == "delete_video_caption":
        execute_query("DELETE FROM video_captions")
        await query.message.reply_text("✅ Video matni o'chirildi! Endi video dan keyin matn chiqmaydi.")
        return
    
    # ---------- HAMKORLAR ----------
    elif data == "manage_partners":
        keyboard = [
            [InlineKeyboardButton("➕ Hamkor qo'shish", callback_data="add_partner")],
            [InlineKeyboardButton("🔍 Hamkorlarni ko'rish", callback_data="view_partners")],
            [InlineKeyboardButton("🗑 Hamkorni o'chirish", callback_data="delete_partner")]
        ]
        await query.message.reply_text(
            "🤝 Hamkorlarni boshqarish:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "add_partner":
        context.user_data.clear()
        context.user_data["action"] = "add_partner"
        await query.message.reply_text("➕ Hamkor matnini yozing (masalan: UC servis @zakirshax):")
        return
    
    elif data == "view_partners":
        partners = fetch_all("SELECT text FROM partners ORDER BY id")
        if partners:
            text = "🤝 Hamkorlar ro'yxati:\n\n" + "\n".join([f"{i+1}. {p[0]}" for i, p in enumerate(partners)])
        else:
            text = "📭 Hali hamkor qo'shilmagan."
        await query.message.reply_text(text)
        return
    
    elif data == "delete_partner":
        context.user_data.clear()
        context.user_data["action"] = "delete_partner"
        partners = fetch_all("SELECT id, text FROM partners ORDER BY id")
        if partners:
            text = "🗑 O'chirish uchun hamkor raqamini yozing:\n\n" + "\n".join([f"{i+1}. {p[1]}" for i, p in enumerate(partners)])
            await query.message.reply_text(text)
        else:
            await query.message.reply_text("❌ O'chirish uchun hamkorlar mavjud emas.")
        return
    
    # ---------- QO'SHIMCHA MATN ----------
    elif data == "manage_text":
        keyboard = [
            [InlineKeyboardButton("➕ Qo'shish", callback_data="add_extra")],
            [InlineKeyboardButton("🔍 Tekshirish", callback_data="check_extra")],
            [InlineKeyboardButton("🗑 O'chirish", callback_data="delete_extra")]
        ]
        await query.message.reply_text(
            "📝 Video tagidagi qo'shimcha matnni boshqarish:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "add_extra":
        context.user_data.clear()
        context.user_data["action"] = "add_extra"
        await query.message.reply_text("✏️ Matnni yozing, u barcha videolarga qo'shiladi:")
        return
    
    elif data == "check_extra":
        films = fetch_all("SELECT code, extra_text FROM films LIMIT 20")
        if films:
            msg = "📝 Videolar va qo'shimcha matn:\n\n"
            for f in films:
                msg += f"📹 {f[0][:20]}{'...' if len(f[0]) > 20 else ''}: {f[1][:50]}{'...' if len(f[1]) > 50 else ''}\n"
            await query.message.reply_text(msg)
        else:
            await query.message.reply_text("📭 Hali videolar yo'q.")
        return
    
    elif data == "delete_extra":
        execute_query("UPDATE films SET extra_text = %s" if DATABASE_URL else "UPDATE films SET extra_text = ?", ('',))
        await query.message.reply_text("✅ Qo'shimcha matn barcha videolardan o'chirildi!")
        return
    
    # ---------- VIDEO O'CHIRISH/TAHRIRLASH ----------
    elif data.startswith("update_"):
        context.user_data.clear()
        old_short_code = data.split("_")[1]
        old_code = get_original_code_from_callback(old_short_code)
        context.user_data["action"] = "update_code"
        context.user_data["old_code"] = old_code
        await query.message.reply_text(f"✏️ Yangi kodni yozing (eski kod: {old_code}):")
        return
    
    elif data.startswith("delete_"):
        short_code = data.split("_")[1]
        code = get_original_code_from_callback(short_code)
        execute_query(
            "DELETE FROM films WHERE code = %s" if DATABASE_URL else "DELETE FROM films WHERE code = ?",
            (code,)
        )
        await query.message.reply_text(f"✅ Video {code} o'chirildi!")
        return
    
    elif data.startswith("edit_caption_"):
        short_code = data.split("_")[2]
        code = get_original_code_from_callback(short_code)
        context.user_data.clear()
        context.user_data["action"] = "edit_video_caption"
        context.user_data["video_code"] = code
        await query.message.reply_text(f"✏️ Video {code} uchun yangi caption yozing:")
        return
    
    # ---------- REKLAMA SOZLAMALARI ----------
    elif data == "ad_settings":
        keyboard = [
            [InlineKeyboardButton("✏️ Reklama matnini o'zgartirish", callback_data="edit_ad_text")],
            [InlineKeyboardButton("🔍 Joriy reklama matni", callback_data="view_ad_text")],
            [InlineKeyboardButton("📨 Kelgan so'rovlar", callback_data="view_requests")]
        ]
        await query.message.reply_text(
            "🎫 Reklama sozlamalari:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "edit_ad_text":
        context.user_data.clear()
        context.user_data["action"] = "edit_ad_text"
        await query.message.reply_text("✏️ Yangi reklama matnini kiriting:")
        return
    
    elif data == "view_ad_text":
        ad_result = fetch_one("SELECT text FROM ad_texts ORDER BY id DESC LIMIT 1")
        if ad_result and ad_result[0]:
            await query.message.reply_text(f"📝 Joriy reklama matni:\n\n{ad_result[0]}")
        else:
            await query.message.reply_text("📭 Hali reklama matni qo'shilmagan.")
        return
    
    elif data == "view_requests":
        requests = fetch_all("""
            SELECT br.user_id, br.request_text, br.request_date 
            FROM bypass_requests br 
            WHERE br.status = 'pending'
            ORDER BY br.request_date DESC
            LIMIT 10
        """)
        
        if not requests:
            await query.message.reply_text("📭 Hozircha yangi so'rovlar yo'q.")
            return
        
        text = "📨 Yangi so'rovlar:\n\n"
        for i, req in enumerate(requests, 1):
            user_id, req_text, req_date = req
            text += f"{i}. 👤 User ID: {user_id}\n"
            text += f"   📅 Sana: {req_date}\n"
            if req_text:
                text += f"   📝 Izoh: {req_text}\n"
            text += "\n"
        
        keyboard = [[InlineKeyboardButton("📋 So'rovlarni boshqarish", callback_data="manage_requests")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif data == "manage_requests":
        context.user_data.clear()
        context.user_data["action"] = "manage_requests"
        requests = fetch_all("SELECT user_id FROM bypass_requests WHERE status = 'pending' ORDER BY request_date")
        
        if not requests:
            await query.message.reply_text("📭 Hozircha yangi so'rovlar yo'q.")
            return
        
        text = "👤 Premium berish uchun user ID ni kiriting:\n\n"
        for i, req in enumerate(requests, 1):
            text += f"{i}. User ID: {req[0]}\n"
        
        await query.message.reply_text(text)
        return
    
    # ---------- PREMIUM BOSHQARISH ----------
    elif data == "premium_management":
        keyboard = [
            [InlineKeyboardButton("👤 Userga premium berish", callback_data="give_premium")],
            [InlineKeyboardButton("📋 Premium foydalanuvchilar", callback_data="list_premium")],
            [InlineKeyboardButton("🗑 Premiumni olib tashlash", callback_data="remove_premium")]
        ]
        await query.message.reply_text(
            "👑 Premium boshqarish:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "give_premium":
        context.user_data.clear()
        context.user_data["action"] = "give_premium_user"
        await query.message.reply_text("👤 Premium beriladigan user ID ni kiriting:")
        return
    
    elif data == "list_premium":
        premium_users = fetch_all("""
            SELECT pu.user_id, pu.expiry_date 
            FROM premium_users pu 
            WHERE pu.expiry_date > CURRENT_TIMESTAMP
            ORDER BY pu.expiry_date
        """)
        
        if not premium_users:
            await query.message.reply_text("📭 Hozircha premium foydalanuvchilar yo'q.")
            return
        
        text = "🎫 Premium foydalanuvchilar:\n\n"
        for i, user in enumerate(premium_users, 1):
            user_id, expiry_date = user
            if isinstance(expiry_date, datetime):
                days_left = (expiry_date - datetime.now()).days
                expiry_str = expiry_date.strftime('%Y-%m-%d')
            elif isinstance(expiry_date, str):
                try:
                    expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    days_left = (expiry_dt - datetime.now()).days
                    expiry_str = expiry_dt.strftime('%Y-%m-%d')
                except:
                    expiry_str = str(expiry_date)
                    days_left = "Noma'lum"
            else:
                expiry_str = str(expiry_date)
                days_left = "Noma'lum"
            
            text += f"{i}. 👤 User ID: {user_id}\n"
            text += f"   📅 Muddati: {expiry_str}\n"
            text += f"   ⏳ Qolgan kun: {days_left}\n\n"
        
        await query.message.reply_text(text)
        return
    
    elif data == "remove_premium":
        context.user_data.clear()
        context.user_data["action"] = "remove_premium_user"
        await query.message.reply_text("🗑 Premium olib tashlanadigan user ID ni kiriting:")
        return

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner video yuklash handler"""
    if update.message.from_user.id != OWNER_ID:
        return
    
    if not update.message.video:
        return
    
    action = context.user_data.get("action")
    
    if action == "broadcast":
        context.user_data["broadcast_video"] = update.message.video.file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("✅ Video qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return
    
    context.user_data["video_file_id"] = update.message.video.file_id
    context.user_data["action"] = "set_code"
    
    is_premium = context.user_data.get("is_premium_video", False)
    if is_premium:
        await update.message.reply_text("🎬 PREMIUM Video qabul qilindi! Endi video uchun kod yoki Instagram linkini yozing:")
    else:
        await update.message.reply_text("✅ Video qabul qilindi! Endi video uchun kod yoki Instagram linkini yozing:")

# ---------- OWNER PHOTO HANDLER ----------
async def handle_owner_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner photo handler"""
    if update.message.from_user.id != OWNER_ID:
        return
    
    action = context.user_data.get("action")
    
    if action == "broadcast":
        context.user_data["broadcast_photo"] = update.message.photo[-1].file_id
        context.user_data["broadcast_caption"] = update.message.caption or ""
        context.user_data["action"] = "confirm_broadcast"
        await update.message.reply_text("✅ Rasm qabul qilindi! Broadcastni boshlash uchun 'HA' yozing yoki bekor qilish uchun boshqa narsa yozing.")
        return

# ---------- PHOTO HANDLER ----------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Photo handler (chek qabul qilish)"""
    user_id = update.message.from_user.id
    
    if user_id == OWNER_ID:
        await handle_owner_photo(update, context)
        return
    
    action = context.user_data.get("action")
    if action == "waiting_receipt":
        photo_file = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        
        try:
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
            
            # Ownerga xabar yuborish
            await context.bot.send_photo(
                OWNER_ID,
                photo_file,
                caption=f"📨 Yangi chek so'rovi!\n\n👤 User ID: {user_id}\n📝 Izoh: {caption}\n\nPremium berish uchun /premium {user_id} 30"
            )
            
            await update.message.reply_text(
                "✅ Chek qabul qilindi! Admin tekshiradi va sizga premium beriladi. "
                "Tasdiqlash uchun biroz kuting."
            )
            
        except Exception as e:
            logger.error(f"Chek saqlashda xatolik: {e}")
            await update.message.reply_text("❌ Xatolik yuz berdi, iltimos qayta urinib ko'ring.")
        
        context.user_data.clear()

# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text message handler"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")
    
    logger.info(f"Text message: user_id={user_id}, text={text}, action={action}")
    
    # ---------- OWNER ACTIONS ----------
    if user_id == OWNER_ID:
        # Video caption tahrirlash
        if action == "edit_video_caption":
            video_code = context.user_data.get("video_code")
            if video_code:
                execute_query(
                    "UPDATE films SET extra_text = %s WHERE code = %s" if DATABASE_URL else "UPDATE films SET extra_text = ? WHERE code = ?",
                    (text, video_code)
                )
                await update.message.reply_text(f"✅ Video {video_code} caption'i yangilandi!")
            context.user_data.clear()
            return
        
        # Video ostidagi matn qo'shish
        if action == "add_video_caption":
            execute_query(
                "INSERT INTO video_captions (caption_text) VALUES (%s)" if DATABASE_URL else "INSERT INTO video_captions (caption_text) VALUES (?)",
                (text,)
            )
            await update.message.reply_text("✅ Video ostidagi matn saqlandi! Endi barcha videolardan keyin bu matn chiqadi.")
            context.user_data.clear()
            return
        
        # Video kodi qo'shish
        if action == "set_code":
            file_id = context.user_data.get("video_file_id")
            is_premium_video = context.user_data.get("is_premium_video", False)
            
            if not file_id:
                await update.message.reply_text("❌ Xatolik! Avval video yuboring.")
                context.user_data.clear()
                return
            
            # Instagram linkini tozalash
            original_text = text
            if 'instagram.com' in text.lower():
                text = clean_instagram_url(text)
                logger.info(f"Tozalangan link: {text} (asl: {original_text})")
            
            # Kod mavjudligini tekshirish
            existing = fetch_one(
                "SELECT * FROM films WHERE code = %s" if DATABASE_URL else "SELECT * FROM films WHERE code = ?",
                (text,)
            )
            
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod/link band! Boshqa kod yoki link kiriting:")
                return
            
            # Video saqlash
            try:
                if DATABASE_URL:
                    execute_query("""
                        INSERT INTO films (code, file_id, is_premium) 
                        VALUES (%s, %s, %s) 
                        ON CONFLICT (code) DO UPDATE SET 
                        file_id = EXCLUDED.file_id, 
                        is_premium = EXCLUDED.is_premium
                    """, (text, file_id, is_premium_video))
                else:
                    execute_query("""
                        INSERT OR REPLACE INTO films (code, file_id, is_premium) 
                        VALUES (?, ?, ?)
                    """, (text, file_id, is_premium_video))
                
                # Video ma'lumotlarini olish
                result = fetch_one(
                    "SELECT extra_text FROM films WHERE code = %s" if DATABASE_URL else "SELECT extra_text FROM films WHERE code = ?",
                    (text,)
                )
                extra_text = result[0] if result else ""
                
                premium_tag = " 🎬 [PREMIUM]" if is_premium_video else ""
                caption_text = f"Kod: {text}\n{extra_text}\n{BOT_USERNAME}"
                
                safe_code = create_safe_callback_data(text)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                     InlineKeyboardButton("📝 Caption o'zgartirish", callback_data=f"edit_caption_{safe_code}")],
                    [InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{safe_code}")]
                ]
                
                await update.message.reply_video(
                    file_id,
                    caption=caption_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                video_type = "PREMIUM video" if is_premium_video else "Video"
                await update.message.reply_text(f"✅ {video_type} saqlandi! Kod: {text}{premium_tag}")
                
            except Exception as e:
                logger.error(f"Video saqlashda xatolik: {e}")
                await update.message.reply_text(f"❌ Xatolik: {e}")
            
            context.user_data.clear()
            return
        
        # Video qidirish
        if action == "search_video":
            original_text = text
            if 'instagram.com' in text.lower():
                text = clean_instagram_url(text)
                logger.info(f"Search tozalangan link: {text} (asl: {original_text})")
            
            result = fetch_one(
                "SELECT file_id, extra_text, is_premium, views FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text, is_premium, views FROM films WHERE code = ?",
                (text,)
            )
            
            if result:
                file_id, extra_text, is_premium_video, views = result
                
                premium_tag = " 🎬 [PREMIUM]" if is_premium_video else ""
                caption_text = f"Kod: {text}\n{extra_text}\n\n👁 Ko'rishlar: {views}\n{BOT_USERNAME}"
                
                safe_code = create_safe_callback_data(text)
                keyboard = [
                    [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{safe_code}"),
                     InlineKeyboardButton("📝 Caption o'zgartirish", callback_data=f"edit_caption_{safe_code}")],
                    [InlineKeyboardButton("❌ Videoni o'chirish", callback_data=f"delete_{safe_code}")]
                ]
                
                await update.message.reply_video(
                    file_id,
                    caption=caption_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await update.message.reply_text(f"✅ Video topildi! Ko'rishlar: {views}{premium_tag}")
            else:
                await update.message.reply_text("❌ Bunday kod/linkka film topilmadi!")
            
            context.user_data.clear()
            return
        
        # Kanal qo'shish
        if action == "add_channel":
            if text.startswith('@'):
                try:
                    if DATABASE_URL:
                        execute_query(
                            "INSERT INTO channels (channel) VALUES (%s) ON CONFLICT (channel) DO NOTHING",
                            (text,)
                        )
                    else:
                        execute_query(
                            "INSERT OR IGNORE INTO channels (channel) VALUES (?)",
                            (text,)
                        )
                    await update.message.reply_text(f"✅ Kanal qo'shildi: {text}")
                except Exception as e:
                    logger.error(f"Kanal qo'shishda xatolik: {e}")
                    await update.message.reply_text(f"❌ Xatolik: {e}")
            else:
                await update.message.reply_text("❌ Kanal nomi @ bilan boshlanishi kerak!")
            
            context.user_data.clear()
            return
        
        # Kanal o'chirish
        if action == "delete_channel":
            execute_query(
                "DELETE FROM channels WHERE channel = %s" if DATABASE_URL else "DELETE FROM channels WHERE channel = ?",
                (text,)
            )
            await update.message.reply_text(f"✅ Kanal o'chirildi: {text}")
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
                
                total = len(users)
                await update.message.reply_text(f"📢 {total} foydalanuvchiga xabar yuborilmoqda...")
                
                for i, user in enumerate(users, 1):
                    try:
                        if broadcast_photo:
                            await context.bot.send_photo(user[0], broadcast_photo, caption=broadcast_caption)
                        elif broadcast_video:
                            await context.bot.send_video(user[0], broadcast_video, caption=broadcast_caption)
                        else:
                            await context.bot.send_message(user[0], broadcast_caption)
                        
                        count += 1
                        
                        # Har 10ta yuborilganda progress xabarini yangilash
                        if i % 10 == 0:
                            await update.message.reply_text(f"📊 Progress: {i}/{total} ({count} muvaffaqiyatli)")
                            
                    except Exception as e:
                        logger.error(f"User {user[0]} ga xabar yuborishda xatolik: {e}")
                        failed += 1
                
                await update.message.reply_text(
                    f"✅ Xabar {count} foydalanuvchiga yuborildi!\n"
                    f"❌ {failed} ta yuborilmadi."
                )
            else:
                await update.message.reply_text("❌ Broadcast bekor qilindi.")
            
            context.user_data.clear()
            return
        
        # Oddiy broadcast
        if action == "broadcast" and not context.user_data.get("broadcast_photo") and not context.user_data.get("broadcast_video"):
            users = fetch_all("SELECT user_id FROM users")
            count = 0
            failed = 0
            
            total = len(users)
            await update.message.reply_text(f"📢 {total} foydalanuvchiga xabar yuborilmoqda...")
            
            for i, user in enumerate(users, 1):
                try:
                    await context.bot.send_message(user[0], text)
                    count += 1
                    
                    if i % 10 == 0:
                        await update.message.reply_text(f"📊 Progress: {i}/{total} ({count} muvaffaqiyatli)")
                        
                except Exception as e:
                    logger.error(f"User {user[0]} ga xabar yuborishda xatolik: {e}")
                    failed += 1
            
            await update.message.reply_text(
                f"✅ Xabar {count} foydalanuvchiga yuborildi!\n"
                f"❌ {failed} ta yuborilmadi."
            )
            context.user_data.clear()
            return
        
        # Qo'shimcha matn qo'shish
        if action == "add_extra":
            execute_query(
                "UPDATE films SET extra_text = %s" if DATABASE_URL else "UPDATE films SET extra_text = ?",
                (text,)
            )
            await update.message.reply_text("✅ Qo'shimcha matn barcha videolarga qo'shildi!")
            context.user_data.clear()
            return
        
        # Video kodi yangilash
        if action == "update_code":
            new_code = text
            old_code = context.user_data.get("old_code")
            
            if 'instagram.com' in new_code.lower():
                new_code = clean_instagram_url(new_code)
                logger.info(f"Update tozalangan link: {new_code}")
            
            # Yangi kod bandligini tekshirish
            existing = fetch_one(
                "SELECT * FROM films WHERE code = %s AND code != %s" if DATABASE_URL else "SELECT * FROM films WHERE code = ? AND code != ?",
                (new_code, old_code)
            )
            
            if existing:
                await update.message.reply_text(f"⚠️ Bu kod band! Boshqa kod kiriting:")
                return
            
            execute_query(
                "UPDATE films SET code = %s WHERE code = %s" if DATABASE_URL else "UPDATE films SET code = ? WHERE code = ?",
                (new_code, old_code)
            )
            
            await update.message.reply_text(f"✅ Video kodi yangilandi! Yangi kod: {new_code}")
            context.user_data.clear()
            return
        
        # Hamkor qo'shish
        if action == "add_partner":
            execute_query(
                "INSERT INTO partners (text) VALUES (%s)" if DATABASE_URL else "INSERT INTO partners (text) VALUES (?)",
                (text,)
            )
            await update.message.reply_text(f"✅ Hamkor qo'shildi: {text}")
            context.user_data.clear()
            return
        
        # Hamkor o'chirish
        if action == "delete_partner":
            try:
                partner_num = int(text)
                partners = fetch_all("SELECT id FROM partners ORDER BY id")
                
                if 1 <= partner_num <= len(partners):
                    partner_id = partners[partner_num-1][0]
                    execute_query(
                        "DELETE FROM partners WHERE id = %s" if DATABASE_URL else "DELETE FROM partners WHERE id = ?",
                        (partner_id,)
                    )
                    await update.message.reply_text(f"✅ Hamkor #{partner_num} o'chirildi!")
                else:
                    await update.message.reply_text("❌ Noto'g'ri raqam!")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, raqam kiriting!")
            
            context.user_data.clear()
            return
        
        # Reklama matnini o'zgartirish
        if action == "edit_ad_text":
            execute_query(
                "INSERT INTO ad_texts (text) VALUES (%s)" if DATABASE_URL else "INSERT INTO ad_texts (text) VALUES (?)",
                (text,)
            )
            await update.message.reply_text("✅ Reklama matni yangilandi!")
            context.user_data.clear()
            return
        
        # So'rovlarni boshqarish
        elif action == "manage_requests":
            try:
                target_user_id = int(text)
                existing = fetch_one(
                    "SELECT * FROM bypass_requests WHERE user_id = %s" if DATABASE_URL else "SELECT * FROM bypass_requests WHERE user_id = ?",
                    (target_user_id,)
                )
                
                if existing:
                    context.user_data["action"] = "set_premium_days"
                    context.user_data["target_user"] = target_user_id
                    await update.message.reply_text(f"👤 User {target_user_id} uchun premium kunlar sonini kiriting (masalan, 30):")
                else:
                    await update.message.reply_text("❌ Bu user ID bo'yicha so'rov topilmadi.")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri user ID kiriting.")
            return
        
        # Premium kunlarini belgilash
        elif action == "set_premium_days":
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
                        """, (target_user_id, expiry_date, OWNER_ID, datetime.now()))
                    
                    # So'rovni o'chirish
                    execute_query(
                        "DELETE FROM bypass_requests WHERE user_id = %s" if DATABASE_URL else "DELETE FROM bypass_requests WHERE user_id = ?",
                        (target_user_id,)
                    )
                    
                    # Userga xabar yuborish
                    try:
                        await context.bot.send_message(
                            target_user_id,
                            f"🎉 Tabriklaymiz! Sizga {days} kunlik premium berildi!\n\n"
                            f"Endi siz kanallarga obuna bo'lish shartisiz botdan foydalana olasiz.\n\n"
                            f"📅 Premium muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}\n"
                            f"🤖 Botdan foydalanish: /start"
                        )
                    except Exception as e:
                        logger.error(f"Userga xabar yuborishda xatolik: {e}")
                    
                    await update.message.reply_text(
                        f"✅ User {target_user_id} ga {days} kunlik premium berildi!\n"
                        f"📅 Muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                    )
                else:
                    await update.message.reply_text("❌ Xatolik! Iltimos, qaytadan urining.")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, kunlar sonini raqamda kiriting.")
            
            context.user_data.clear()
            return
        
        # Userga premium berish
        elif action == "give_premium_user":
            try:
                target_user_id = int(text)
                context.user_data["action"] = "set_premium_days_direct"
                context.user_data["target_user"] = target_user_id
                await update.message.reply_text(f"👤 User {target_user_id} uchun premium kunlar sonini kiriting:")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri user ID kiriting.")
            return
        
        # To'g'ridan-to'g'ri premium berish
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
                        """, (target_user_id, expiry_date, OWNER_ID, datetime.now()))
                    
                    await update.message.reply_text(
                        f"✅ User {target_user_id} ga {days} kunlik premium berildi!\n"
                        f"📅 Muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                    )
                else:
                    await update.message.reply_text("❌ Xatolik! Iltimos, qaytadan urining.")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, kunlar sonini raqamda kiriting.")
            
            context.user_data.clear()
            return
        
        # Premiumni olib tashlash
        elif action == "remove_premium_user":
            try:
                target_user_id = int(text)
                execute_query(
                    "DELETE FROM premium_users WHERE user_id = %s" if DATABASE_URL else "DELETE FROM premium_users WHERE user_id = ?",
                    (target_user_id,)
                )
                await update.message.reply_text(f"✅ User {target_user_id} ning premiumi olib tashlandi!")
            except ValueError:
                await update.message.reply_text("❌ Iltimos, to'g'ri user ID kiriting.")
            
            context.user_data.clear()
            return
    
    # ---------- FOYDALANUVCHI KINO QIDIRISH ----------
    # Instagram linkini tozalash
    original_user_text = text
    if 'instagram.com' in text.lower():
        text = clean_instagram_url(text)
        logger.info(f"User tozalangan link: {text} (asl: {original_user_text})")
    
    result = fetch_one(
        "SELECT file_id, extra_text, is_premium FROM films WHERE code = %s" if DATABASE_URL else "SELECT file_id, extra_text, is_premium FROM films WHERE code = ?",
        (text,)
    )
    
    if result:
        file_id, extra_text, is_premium_video = result
        
        # Premium video tekshirish
        if is_premium_video and not is_premium_user(user_id):
            await update.message.reply_text(
                "❌ SIZ PREMIUM OBUNACHI EMASSIZ!\n\n"
                "Bu video faqat premium foydalanuvchilar uchun mavjud.\n\n"
                "Premium obuna sotib olish uchun quyidagi tugmani bosing:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎫 PREMIUM SOTIB OLISH", callback_data="buy_premium")]
                ])
            )
            return
        
        # Video kodini saqlash
        context.user_data["last_video_code"] = text
        
        # Ko'rishlar sonini oshirish
        increment_video_views(text)
        
        # Statistika olish
        view_count = fetch_one(
            "SELECT views FROM films WHERE code = %s" if DATABASE_URL else "SELECT views FROM films WHERE code = ?",
            (text,)
        )
        views = view_count[0] if view_count else 0
        
        is_premium = is_premium_user(user_id)
        
        if is_premium:
            caption = f"Kod: {original_user_text}\n{extra_text}\n\n👁 Ko'rishlar: {views}\n{BOT_USERNAME}"
            await update.message.reply_video(file_id, caption=caption)
            await send_video_caption(update, context)
        else:
            channels = fetch_all("SELECT channel FROM channels")
            not_subscribed = []
            
            for channel in channels:
                try:
                    member = await context.bot.get_chat_member(channel[0], user_id)
                    if member.status in ["left", "kicked"]:
                        not_subscribed.append(channel[0])
                except Exception as e:
                    logger.error(f"Kanal tekshirish xatolik: {e}")
                    not_subscribed.append(channel[0])
            
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
                caption = f"Kod: {original_user_text}\n{extra_text}\n\n👁 Ko'rishlar: {views}\n{BOT_USERNAME}"
                await update.message.reply_video(file_id, caption=caption)
                await send_video_caption(update, context)
    else:
        await update.message.reply_text("❌ Bunday kod/linkka film topilmadi! Iltimos, to'g'ri kod yoki linkni yuboring.")

# ---------- PREMIUM COMMAND ----------
async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium berish komandasi (faqat owner uchun)"""
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Bu komanda faqat admin uchun!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Foydalanish: /premium [user_id] [kunlar]\nMisol: /premium 123456789 30")
        return
    
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        
        if days <= 0:
            await update.message.reply_text("❌ Kunlar soni musbat bo'lishi kerak!")
            return
        
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
            """, (user_id, expiry_date, OWNER_ID, datetime.now()))
        
        await update.message.reply_text(
            f"✅ User {user_id} ga {days} kunlik premium berildi!\n"
            f"📅 Muddati: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
        )
        
        try:
            await context.bot.send_message(
                user_id,
                f"🎉 Tabriklaymiz! Sizga {days} kunlik premium berildi!\n\n"
                f"Endi siz kanallarga obuna bo'lish shartisiz botdan foydalana olasiz."
            )
        except Exception as e:
            logger.error(f"Userga xabar yuborishda xatolik: {e}")
            
    except ValueError:
        await update.message.reply_text("❌ Xatolik! User ID va kunlar sonini to'g'ri kiriting.")
    except Exception as e:
        logger.error(f"Premium command xatolik: {e}")
        await update.message.reply_text(f"❌ Xatolik: {e}")

# ---------- ERROR HANDLER ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni qayta ishlash"""
    logger.error(f"Xatolik yuz berdi: {context.error}")
    
    try:
        if update and update.effective_user:
            await context.bot.send_message(
                update.effective_user.id,
                "❌ Xatolik yuz berdi, iltimos keyinroq urinib ko'ring."
            )
    except:
        pass

# ---------- MAIN FUNCTION ----------
def main():
    """Asosiy funksiya"""
    # Database ni ishga tushirish
    init_database()
    
    # Application yaratish
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shish
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(InlineQueryHandler(handle_inline_query))
    app.add_handler(ChosenInlineResultHandler(handle_chosen_inline_result))
    
    # Xatolik handler
    app.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    logger.info("🤖 Bot ishga tushmoqda...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

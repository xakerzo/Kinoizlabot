import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    filters
)

# ---------- TOKEN VA OWNER ----------
BOT_TOKEN = os.getenv("TOKEN")           # Railway Environment Variable
OWNER_ID = int(os.getenv("OWNER_ID"))    # Railway Environment Variable
BOT_USERNAME = "@YourBotUsername"        # O'zingizning bot username

# ---------- DATABASE ----------
conn = sqlite3.connect("films.db", check_same_thread=False)
cursor = conn.cursor()

# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Kino botga xush kelibsiz.")

# ---------- CALLBACK HANDLER ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Bu yerda sizning oldingi callback logikangiz ishlaydi
    # Masalan: update_{code}, delete_{code}, check_subs_{code}...

# ---------- OWNER VIDEO HANDLER ----------
async def handle_owner_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sizning video upload va kodni yangilash logikangiz shu yerda
    pass

# ---------- TEXT HANDLER ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    # ---------- KOD YANGILASH ----------
    old_code = context.user_data.get("old_code")
    if old_code:
        new_code = text
        cursor.execute("UPDATE films SET code=? WHERE code=?", (new_code, old_code))
        conn.commit()
        cursor.execute("SELECT file_id, extra_text FROM films WHERE code=?", (new_code,))
        result = cursor.fetchone()
        if result:
            file_id, extra_text = result
            keyboard = [
                [InlineKeyboardButton("✏️ Kodni alishtirish", callback_data=f"update_{new_code}"),
                 InlineKeyboardButton("❌ Videoni o‘chirish", callback_data=f"delete_{new_code}")]
            ]
            await update.message.reply_video(file_id, reply_markup=InlineKeyboardMarkup(keyboard), caption=f"Kod: {new_code}\n{extra_text}\n{BOT_USERNAME}")
        await update.message.reply_text(f"Video kodi yangilandi! Yangi kod: {new_code}")
        context.user_data.clear()
        return

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
app.add_handler(MessageHandler(filters.VIDEO, handle_owner_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.run_polling()

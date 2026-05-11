import os

# Telegram Bot Config
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_ID = int(os.environ.get('OWNER_ID', '1373647'))
ADMIN_IDS = [OWNER_ID]  # Add other admin IDs here if needed

# Database Config
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_NAME = "kino_bot.db"

# Click Config
CLICK_MERCHANT_ID = os.environ.get('CLICK_MERCHANT_ID')
CLICK_SERVICE_ID = os.environ.get('CLICK_SERVICE_ID')
CLICK_SECRET_KEY = os.environ.get('CLICK_SECRET_KEY')

# Payme Config
PAYME_MERCHANT_ID = os.environ.get('PAYME_MERCHANT_ID', 'your_merchant_id')
PAYME_TOKEN = os.environ.get('PAYME_TOKEN', 'your_payme_token')

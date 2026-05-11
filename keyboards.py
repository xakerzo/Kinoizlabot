from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def vip_tariffs_buttons(tariffs):
    """
    tariffs: list of tuples (id, price, days)
    """
    keyboard = []
    for t_id, price, days in tariffs:
        keyboard.append([InlineKeyboardButton(f"💎 {days} kun - {price} so'm", callback_data=f"buy_premium_{t_id}")])
    return InlineKeyboardMarkup(keyboard)

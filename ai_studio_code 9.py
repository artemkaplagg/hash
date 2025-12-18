from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    """Створює головне меню бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Допоможи з ДЗ"), KeyboardButton(text="📝 Перевір твір")],
            [KeyboardButton(text="⚙️ Налаштування"), KeyboardButton(text="❓ Допомога")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши питання або надішли фото..."
    )
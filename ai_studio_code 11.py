import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config, setup_logging
from handlers import messages
from keyboards.main_kb import get_main_menu

async def main():
    # Налаштовуємо логування
    setup_logging()
    
    # Створюємо екземпляр бота
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    dp = Dispatcher()
    
    # Підключаємо наші обробники
    dp.include_router(messages.router)
    
    # Обробка команди /start
    @dp.message(lambda m: m.text == "/start")
    async def cmd_start(message: types.Message):
        await message.answer(
            f"Привіт, {message.from_user.first_name}! 👋\nЯ твій ШІ-репетитор. Надішли мені текст або фото завдання.",
            reply_markup=get_main_menu()
        )

    print("🚀 Бот запущений у Termux! Натисніть Ctrl+C для зупинки.")
    
    # Очищуємо чергу повідомлень та запускаємо бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот вимкнений.")
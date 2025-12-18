import io
from aiogram import Router, types, F, Bot
from aiogram.utils.chat_action import ChatActionSender
from services.ai_service import ai_service

router = Router()

@router.message(F.photo)
async def handle_photo(message: types.Message, bot: Bot):
    """Обробка фотографій із завданнями."""
    # Показуємо статус "завантаження фото"
    async with ChatActionSender.upload_photo(chat_id=message.chat.id, bot=bot):
        # Беремо фото найкращої якості
        photo = message.photo[-1]
        file_io = io.BytesIO()
        
        # Завантажуємо файл з серверів Telegram
        file = await bot.get_file(photo.file_id)
        await bot.download_file(file.file_path, file_io)
        
        prompt = message.caption if message.caption else "Розв'яжи завдання на цьому фото та поясни кроки."
        
        # Відправляємо в ШІ
        async with ChatActionSender.typing(chat_id=message.chat.id, bot=bot):
            answer = await ai_service.generate_answer(prompt, file_io.getvalue())
            await message.reply(answer)

@router.message(F.text)
async def handle_text(message: types.Message, bot: Bot):
    """Обробка звичайних текстових питань."""
    # Пропускаємо системні кнопки
    if message.text.startswith("⚙️") or message.text.startswith("❓"):
        await message.answer("Ця функція в розробці. Просто напиши своє питання!")
        return

    async with ChatActionSender.typing(chat_id=message.chat.id, bot=bot):
        answer = await ai_service.generate_answer(message.text)
        # Якщо відповідь занадто довга, Telegram її не пропустить (ліміт 4096)
        if len(answer) > 4000:
            for x in range(0, len(answer), 4000):
                await message.answer(answer[x:x+4000])
        else:
            await message.answer(answer)
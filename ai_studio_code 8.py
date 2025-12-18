import google.generativeai as genai
import logging
import asyncio
from config import config

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        # Налаштування API з використанням REST для стабільності в Termux
        genai.configure(api_key=config.GEMINI_API_KEY.get_secret_value(), transport='rest')
        
        # Список моделей для "відкату", якщо одна не працює
        self.models_to_try = [config.MODEL_NAME, "gemini-1.5-flash", "gemini-1.5-pro"]
        
    async def generate_answer(self, prompt: str, image_bytes: bytes = None) -> str:
        """Відправляє запит до ШІ та повертає відповідь."""
        for model_name in self.models_to_try:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction="Ти — крутий шкільний вчитель. Пояснюй завдання просто, з прикладами, українською мовою."
                )
                
                content = []
                if image_bytes:
                    content.append({"mime_type": "image/jpeg", "data": image_bytes})
                content.append(prompt)

                # Асинхронний запит до Google
                response = await model.generate_content_async(content)
                
                if response and response.text:
                    return response.text
                return "Хмм, ШІ не зміг придумати відповідь. Спробуй ще раз."

            except Exception as e:
                err_msg = str(e)
                logger.error(f"Помилка моделі {model_name}: {err_msg}")
                
                if "429" in err_msg:
                    # Якщо ліміт вичерпано, чекаємо 2 сек і пробуємо наступну модель
                    await asyncio.sleep(2)
                    continue
                elif "404" in err_msg:
                    # Якщо модель не знайдена, пробуємо наступну
                    continue
                
                return f"❌ Сталася помилка: {err_msg[:100]}..."
        
        return "⚠️ На жаль, зараз всі лінії ШІ перевантажені. Спробуй через 5 хвилин."

ai_service = GeminiService()
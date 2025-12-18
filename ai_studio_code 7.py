import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    # Твій новий токен від @BotFather
    BOT_TOKEN: SecretStr = "8591326155:AAGae13tPYWYSFKM5rx_Ep8rMTWoH3IxqyU"
    # Твій НОВИЙ ключ від Google AI Studio
    GEMINI_API_KEY: SecretStr = "AIzaSyACmMGY6yK0VAeKAFk0Ynh8bY0m58RLKzI"
    
    # Використовуємо 2.0 Flash як основну (актуальна на кінець 2025)
    MODEL_NAME: str = "gemini-2.0-flash"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
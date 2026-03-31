import os
import sys

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    sys.exit("ERROR: BOT_TOKEN not set")

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
if not OWNER_ID:
    sys.exit("ERROR: OWNER_ID not set")

DB_PATH = "monarch.db"

# 3 фото — вставь file_id или прямую ссылку после того как загрузишь
PHOTO_MORNING = os.getenv("PHOTO_MORNING", "")   # 06:00 - 12:00
PHOTO_DAY     = os.getenv("PHOTO_DAY",     "")   # 12:00 - 18:00
PHOTO_EVENING = os.getenv("PHOTO_EVENING", "")   # 18:00 - 00:00

# Через сколько минут можно снова отправить фото при /start
PHOTO_COOLDOWN_MIN = 60

TZ_OFFSET = 3  # UTC+3 Киев

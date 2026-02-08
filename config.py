import os
import json
from dotenv import load_dotenv

# Принудительно перезагружаем .env
load_dotenv(override=True)

# --- Credentials ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Sheets Config
SHEET_ID = os.getenv("SHEET_ID")
TAB_NAME = os.getenv("TAB_NAME", "WeeklyData")

# --- Google Service Account Key ---
if os.getenv("GOOGLE_SA_JSON"):
    GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON")
else:
    try:
        with open("google_key.json", "r", encoding="utf-8") as f:
            GOOGLE_SA_JSON = f.read()
    except FileNotFoundError:
        print("ОШИБКА: Не найден GOOGLE_SA_JSON в .env и отсутствует файл google_key.json")
        GOOGLE_SA_JSON = None

# --- Security ---
ALLOWED_IDS = [int(x) for x in os.getenv("ALLOWED_IDS", "").split(",") if x]

# --- Column Mapping ---
# ИСПРАВЛЕНО: Ключи обновлены на car_insurance и trailer_insurance
CATEGORIES_MAP = {
    "gross": "C",             # Gross Pay
    "fuel": "D",              # Fuel
    "dispatch_fee": "E",      # Dispatch Fee
    "car_insurance": "F",     # <--- БЫЛО phys_dam (Теперь Car Insurance)
    "credit": "G",            # Credit
    "trailer_rent": "H",      # Trailer Rent
    "cargo_liab": "I",        # Cargo Liability
    "samsara": "J",           # Samsara/ELD
    "logbook": "K",           # Logbook
    "reg_account": "L",       # Registration/Plates
    "trailer_insurance": "M", # <--- БЫЛО phys_trailer (Теперь Trailer Insurance)
    "other": "N"              # Прочее
}

# Колонка, где бот ищет диапазоны дат (недель)
DATE_COLUMN = "B"
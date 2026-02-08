import os
from dotenv import load_dotenv

# Загружаем .env, но НЕ перезаписываем переменные окружения (убрали override=True)
load_dotenv()

# --- Credentials ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка на наличие токена
if not TELEGRAM_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден! Проверьте переменные окружения.")

# Google Sheets Config
SHEET_ID = os.getenv("SHEET_ID")
TAB_NAME = os.getenv("TAB_NAME", "WeeklyData")

# --- Google Service Account Key ---
if os.getenv("GOOGLE_SA_JSON"):
    GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON")
else:
    try:
        if os.path.exists("google_key.json"):
            with open("google_key.json", "r", encoding="utf-8") as f:
                GOOGLE_SA_JSON = f.read()
        else:
            GOOGLE_SA_JSON = None
    except Exception as e:
        print(f"Ошибка чтения ключа: {e}")
        GOOGLE_SA_JSON = None

# --- Security ---
ALLOWED_IDS = []
ids_env = os.getenv("ALLOWED_IDS", "")
if ids_env:
    try:
        ALLOWED_IDS = [int(x.strip()) for x in ids_env.split(",") if x.strip()]
    except ValueError:
        pass

# --- Column Mapping ---
CATEGORIES_MAP = {
    "gross": "C",             
    "fuel": "D",              
    "dispatch_fee": "E",      
    "car_insurance": "F",     
    "credit": "G",            
    "trailer_rent": "H",      
    "cargo_liab": "I",        
    "samsara": "J",           
    "logbook": "K",           
    "reg_account": "L",       
    "trailer_insurance": "M", 
    "other": "N"              
}

DATE_COLUMN = "B"

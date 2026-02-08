from datetime import date, timedelta, datetime
import re

def parse_date(date_input: str) -> date:
    """
    Парсит дату из строки.
    1. Понимает цифры (01.25.2026) — СТАРАЯ ЛОГИКА.
    2. Понимает буквы (Jun 4, 2025) — НОВАЯ ЛОГИКА.
    """
    if not date_input:
        return date.today()
    
    s = str(date_input).strip().lower()
    
    # Ключевые слова
    if s in ["today", "сегодня", "now"]:
        return date.today()
    if s in ["yesterday", "вчера"]:
        return date.today() - timedelta(days=1)
        
    # === ПОПЫТКА 1: ЦИФРОВОЙ ФОРМАТ (Старый метод) ===
    # Заменяем всё на точки: 01/02/2026 -> 01.02.2026
    s_numeric = s.replace(",", ".").replace("/", ".").replace("-", ".")
    
    numeric_formats = ["%m.%d.%Y", "%d.%m.%Y", "%Y.%m.%d", "%m.%d.%y"]
    
    for fmt in numeric_formats:
        try:
            return datetime.strptime(s_numeric, fmt).date()
        except ValueError:
            continue

    # === ПОПЫТКА 2: ТЕКСТОВЫЙ ФОРМАТ (Новый метод) ===
    # Jun 4, 2025 -> jun 4 2025 (убираем запятые и точки, оставляем пробелы)
    s_text = s.replace(",", " ").replace(".", " ").replace("/", " ").replace("-", " ")
    s_text = " ".join(s_text.split()) # Убираем двойные пробелы
    
    text_formats = [
        "%b %d %Y",     # jun 4 2025 (short month)
        "%B %d %Y",     # june 4 2025 (full month)
        "%d %b %Y",     # 4 jun 2025
        "%d %B %Y",     # 4 june 2025
    ]
    
    for fmt in text_formats:
        try:
            return datetime.strptime(s_text, fmt).date()
        except ValueError:
            continue
            
    # === Fallback: Ищем паттерн цифр (из старого кода) ===
    match = re.search(r"(\d{1,2})[\./-](\d{1,2})[\./-](\d{2,4})", s_numeric)
    if match:
        try:
            # Пытаемся угадать US format (MM/DD/YYYY) по умолчанию
            return datetime.strptime(match.group(0).replace("-", "."), "%m.%d.%Y").date()
        except:
            pass
            
    # Если совсем ничего не поняли — возвращаем сегодня
    return date.today()

def get_week_range(d: date) -> str:
    """
    Возвращает диапазон: Понедельник - Воскресенье.
    Пример: 01.26.2026-02.01.2026
    """
    # d.weekday(): 0=Mon, 1=Tue, ..., 6=Sun
    start_date = d - timedelta(days=d.weekday())
    end_date = start_date + timedelta(days=6)
    
    fmt = "%m.%d.%Y"
    return f"{start_date.strftime(fmt)}-{end_date.strftime(fmt)}"

def normalize_week_string(s: str) -> str:
    """Убирает все кроме цифр для сравнения"""
    return re.sub(r"\D", "", str(s))
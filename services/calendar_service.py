from datetime import date, timedelta, datetime
import re

# === НАСТРОЙКА ВРЕМЕНИ (US TIME) ===
# Сдвиг -7 часов (примерно Denver/Mountain Time).
# Это нужно, чтобы когда в США воскресенье вечер, бот не думал, что уже понедельник (UTC).
TIMEZONE_OFFSET = -7 

def get_current_date_us():
    """Возвращает текущую дату США (с учетом сдвига), а не UTC."""
    return (datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)).date()

def parse_date(date_input: str) -> date:
    """
    Парсит дату. 
    СТРОГИЙ ПРИОРИТЕТ: Американский формат (MM.DD).
    """
    today_us = get_current_date_us()
    
    if not date_input:
        return today_us
    
    s = str(date_input).strip().lower()
    
    # Ключевые слова
    if s in ["today", "сегодня", "now"]:
        return today_us
    if s in ["yesterday", "вчера"]:
        return today_us - timedelta(days=1)
        
    # Чистим строку: 08-02 -> 08.02
    s_numeric = s.replace(",", ".").replace("/", ".").replace("-", ".")
    
    # === 1. ПОЛНЫЙ ФОРМАТ (MM.DD.YYYY) ===
    # Сначала проверяем американский формат: Месяц.День.Год
    full_formats = ["%m.%d.%Y", "%Y.%m.%d"]
    for fmt in full_formats:
        try:
            return datetime.strptime(s_numeric, fmt).date()
        except ValueError:
            continue

    # === 2. КОРОТКИЙ ФОРМАТ (MM.DD) ===
    # ВАЖНО: Приоритет Месяц.День
    # 08.02 -> Август (08), 2-е число.
    # 02.08 -> Февраль (02), 8-е число.
    short_formats = ["%m.%d"]
    
    for fmt in short_formats:
        try:
            dt = datetime.strptime(s_numeric, fmt)
            dt = dt.replace(year=today_us.year)
            return dt.date()
        except ValueError:
            continue

    # === 3. ТЕКСТОВЫЙ ФОРМАТ ===
    # Jun 4 ...
    s_text = s.replace(",", " ").replace(".", " ").replace("/", " ").replace("-", " ")
    s_text = " ".join(s_text.split())
    
    text_formats = [
        "%b %d %Y", "%B %d %Y", # Jun 4 2026
        "%b %d", "%B %d"        # Jun 4
    ]
    
    for fmt in text_formats:
        try:
            dt = datetime.strptime(s_text, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=today_us.year)
            return dt.date()
        except ValueError:
            continue
            
    # Fallback: если ничего не подошло, пробуем найти цифры и считаем их MM.DD
    match = re.search(r"(\d{1,2})[\./-](\d{1,2})", s_numeric)
    if match:
        try:
            # Group 1 = Month, Group 2 = Day
            m, d = int(match.group(1)), int(match.group(2))
            return date(today_us.year, m, d)
        except:
            pass

    return today_us

def get_week_range(d: date) -> str:
    """
    Возвращает диапазон: Понедельник - Воскресенье.
    """
    # d.weekday(): 0=Mon, ... 6=Sun
    start_date = d - timedelta(days=d.weekday())
    end_date = start_date + timedelta(days=6)
    fmt = "%m.%d.%Y"
    return f"{start_date.strftime(fmt)}-{end_date.strftime(fmt)}"

def normalize_week_string(s: str) -> str:
    return re.sub(r"\D", "", str(s))

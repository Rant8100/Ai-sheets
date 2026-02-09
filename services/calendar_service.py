from datetime import date, timedelta, datetime
import re

def parse_date(date_input: str) -> date:
    """
    Парсит дату из строки.
    1. Понимает цифры (01.25.2026).
    2. Понимает короткие даты (02.08) -> подставляет текущий год.
    3. Понимает слова (Jun 4, 2025).
    """
    if not date_input:
        return date.today()
    
    s = str(date_input).strip().lower()
    today = date.today()
    
    # Ключевые слова
    if s in ["today", "сегодня", "now"]:
        return today
    if s in ["yesterday", "вчера"]:
        return today - timedelta(days=1)
        
    # === ПОДГОТОВКА: Заменяем все разделители на точки ===
    # 08/02 -> 08.02, 08-02 -> 08.02
    s_numeric = s.replace(",", ".").replace("/", ".").replace("-", ".")
    
    # === ПОПЫТКА 1: ПОЛНЫЙ ФОРМАТ (с годом) ===
    full_formats = ["%m.%d.%Y", "%d.%m.%Y", "%Y.%m.%d", "%m.%d.%y"]
    for fmt in full_formats:
        try:
            return datetime.strptime(s_numeric, fmt).date()
        except ValueError:
            continue

    # === ПОПЫТКА 2: КОРОТКИЙ ФОРМАТ (без года) — ЭТО ТО, ЧТО ТЫ ПРОСИЛ ===
    # Если ввели "08.02", пробуем добавить текущий год
    short_formats = ["%m.%d", "%d.%m"]
    for fmt in short_formats:
        try:
            # strptime ("08.02", "%m.%d") создаст дату в 1900 году
            dt = datetime.strptime(s_numeric, fmt)
            # Заменяем год на текущий (2026)
            return dt.replace(year=today.year).date()
        except ValueError:
            continue

    # === ПОПЫТКА 3: ТЕКСТОВЫЙ ФОРМАТ ===
    # Jun 4, 2025 -> jun 4 2025
    s_text = s.replace(",", " ").replace(".", " ").replace("/", " ").replace("-", " ")
    s_text = " ".join(s_text.split())
    
    text_formats = [
        "%b %d %Y",     # jun 4 2025
        "%B %d %Y",     # june 4 2025
        "%d %b %Y",     # 4 jun 2025
        "%d %B %Y",     # 4 june 2025
        "%b %d",        # jun 4 (без года)
        "%d %b"         # 4 jun (без года)
    ]
    
    for fmt in text_formats:
        try:
            dt = datetime.strptime(s_text, fmt)
            # Если год 1900 (значит формат был без года), ставим текущий
            if dt.year == 1900:
                dt = dt.replace(year=today.year)
            return dt.date()
        except ValueError:
            continue
            
    # === Fallback: Если ничего не подошло, но там есть цифры ===
    # Пытаемся вытащить хоть что-то похожее на дату
    match = re.search(r"(\d{1,2})[\./-](\d{1,2})", s_numeric)
    if match:
        try:
            # Считаем, что это Месяц.День текущего года
            m, d = int(match.group(1)), int(match.group(2))
            return date(today.year, m, d)
        except:
            pass
            
    # Если совсем ничего не поняли — возвращаем сегодня
    return today

def get_week_range(d: date) -> str:
    """
    Возвращает диапазон: Понедельник - Воскресенье.
    Пример: 01.26.2026-02.01.2026
    """
    start_date = d - timedelta(days=d.weekday())
    end_date = start_date + timedelta(days=6)
    fmt = "%m.%d.%Y"
    return f"{start_date.strftime(fmt)}-{end_date.strftime(fmt)}"

def normalize_week_string(s: str) -> str:
    return re.sub(r"\D", "", str(s))

import base64
import json
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, CATEGORIES_MAP

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ==============================================================================
# 1. ПРОМПТ ДЛЯ СТЕЙТМЕНТОВ (Логика сохранена + добавлено правило null)
# ==============================================================================
PROMPT_STATEMENT = f"""
Ты — профессиональный бухгалтер для траковой компании.
Твоя задача: проанализировать Driver Settlement (Зарплатный лист) и извлечь транзакции.

ДОСТУПНЫЕ КАТЕГОРИИ: {list(CATEGORIES_MAP.keys())}

ПРАВИЛА АНАЛИЗА (СТРОГО):

1. ДАТА (DATE) - ФОРМАТ MM.DD.YYYY:
   - ИГНОРИРУЙ дату документа в шапке.
   - СМОТРИ В ТАБЛИЦУ ГРУЗОВ (Loads). Найди колонку "Delivery".
   - Выбери ПОСЛЕДНЮЮ дату выгрузки.
   - ПРЕВРАЩАЙ ЛЮБОЙ ФОРМАТ В ЦИФРЫ: "Jun 4, 2025" -> "06.04.2025".
   - ВАЖНО: Если ты не можешь найти дату выгрузки — верни null.

2. GROSS PAY (Грязными):
   - Ищи колонку "Rate" или "Total Revenue" (100% сумма). Не бери Amount.

3. ВЫЧЕТЫ (Deductions):
   - "Deposit" -> ВСЕГДА category: "other".
   - "Trailer Rent" (без слова Deposit) -> category: "trailer_rent".

4. СТРАХОВКИ:
   - "Physical Damage"/"Bobtail" -> "car_insurance".
   - "Trailer Insurance" -> "trailer_insurance".

5. ОСТАЛЬНОЕ:
   - Fuel -> "fuel".
   - Dispatch Fee -> "dispatch_fee".
   - Samsara/Logbook -> "samsara".

ФОРМАТ ОТВЕТА (JSON):
{{ "date": "MM.DD.YYYY" или null, "items": [ {{ "category": "...", "amount": 0.0, "description": "..." }} ] }}
"""

# ==============================================================================
# 2. ПРОМПТ ДЛЯ ТОПЛИВА (Логика сохранена + добавлено правило null)
# ==============================================================================
PROMPT_FUEL = f"""
Ты — бухгалтер по топливу. Анализируешь топливные отчеты или чеки.

ДОСТУПНЫЕ КАТЕГОРИИ: {list(CATEGORIES_MAP.keys())}

ПРАВИЛА:
1. ДАТА - ФОРМАТ MM.DD.YYYY:
   - Приоритет №1: "End Period", "Period Ending".
   - Приоритет №2: Дата транзакции (Transaction Date).
   - КОНВЕРТИРУЙ: "Jun 4, 2025" -> "06.04.2025".
   - ВАЖНО: Если даты нет — верни null.

2. СУММА (Net Payables):
   - Ищи "Total Payables After Discount" или "Total Payables After Non-Cash Adjustment".
   - Нам нужна сумма МЕНЬШАЯ (после скидок).
   - Категория ВСЕГДА "fuel".

ФОРМАТ ОТВЕТА (JSON):
{{ "date": "MM.DD.YYYY" или null, "items": [ {{ "category": "fuel", "amount": 0.0, "description": "..." }} ] }}
"""

# ==============================================================================
# 3. ПРОМПТ ОБЩИЙ (Здесь главное изменение для голосовых)
# ==============================================================================
PROMPT_GENERAL = f"""
Ты — бухгалтер. Анализируешь чеки (Receipts), инвойсы, фото и ТЕКСТОВЫЕ/ГОЛОСОВЫЕ заметки.

ДОСТУПНЫЕ КАТЕГОРИИ: {list(CATEGORIES_MAP.keys())}

ПРАВИЛА:
1. ДАТА (DATE):
   - Если дата четко указана (на чеке или в тексте "вчера купил...") -> используй её (MM.DD.YYYY).
   - ВАЖНО: Если даты НЕТ и контекст не ясен (например, просто "10 топливо") -> ВЕРНИ null. 
   - НЕ ПРИДУМЫВАЙ "сегодняшнюю" дату. Оставь null, я спрошу у пользователя.

2. КАТЕГОРИИ:
   - "Ремонт колеса", "Tire" -> "other".
   - "Trailer Insurance" -> "trailer_insurance".
   - "Car Insurance" -> "car_insurance".
   - "Солярка", "Fuel", "Дизель" -> "fuel".

ФОРМАТ ОТВЕТА (JSON):
{{ "date": "MM.DD.YYYY" или null, "items": [ {{ "category": "...", "amount": 0.0, "description": "..." }} ] }}
"""

async def analyze_content(text: str = None, image_bytes: bytes = None, doc_type: str = "general"):
    if doc_type == "statement":
        system_prompt = PROMPT_STATEMENT
    elif doc_type == "fuel":
        system_prompt = PROMPT_FUEL
    else:
        system_prompt = PROMPT_GENERAL

    messages = [{"role": "system", "content": system_prompt}]
    
    user_content = []
    if text:
        user_content.append({"type": "text", "text": f"Данные:\n{text}"})
        
    if image_bytes:
        b64_image = base64.b64encode(image_bytes).decode('utf-8')
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
        })
        
    if not user_content:
        return None
        
    messages.append({"role": "user", "content": user_content})
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        return None

async def transcribe_audio(file_path):
    with open(file_path, "rb") as audio:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio
        )
    return transcript.text

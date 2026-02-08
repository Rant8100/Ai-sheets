import os
import logging
import asyncio
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler

from config import TELEGRAM_TOKEN, ALLOWED_IDS, CATEGORIES_MAP
from services.ai_service import analyze_content, transcribe_audio
from services.file_processor import extract_text_from_pdf
from services.calendar_service import parse_date, get_week_range
from services.sheet_service import get_worksheet, find_row_by_week, update_cell_with_note

# --- Состояния разговора ---
WAITING_FOR_DOC_TYPE = 1  # Ждем нажатия кнопки
WAITING_FOR_DATE = 2      # Ждем ввода даты вручную

# --- Настройка логов ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def check_auth(update: Update):
    """Проверка прав доступа"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_IDS:
        await update.message.reply_text(f"⛔ Access denied. Your ID: {user_id}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text("🚛 FinBot v3.5 готов!\nКидай PDF, фото, голосовые или текст.")

async def process_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Главная функция приема сообщений.
    1. Если Текст/Голос -> сразу анализируем (General).
    2. Если Файл/Фото -> сохраняем и показываем кнопки выбора.
    """
    if not await check_auth(update): return
    
    msg = update.message
    
    # --- СЦЕНАРИЙ 1: ГОЛОС или ТЕКСТ (без фото) ---
    if msg.voice or (msg.text and not msg.photo):
        status_msg = await msg.reply_text("⏳ Анализирую...")
        
        text_content = ""
        # Если текст
        if msg.text:
            text_content = msg.text
            
        # Если голос
        elif msg.voice:
            # --- ИСПРАВЛЕНИЕ WINDOWS ERROR ---
            temp_path = ""
            # Создаем файл, закрываем его, и только потом используем
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                temp_path = tmp.name
            
            try:
                file = await msg.voice.get_file()
                await file.download_to_drive(temp_path)
                text_content = await transcribe_audio(temp_path)
            finally:
                # Удаляем файл даже если произошла ошибка
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            await status_msg.edit_text(f"🗣 Распознано: {text_content}\n🧠 Думаю...")

        # Запускаем анализ сразу как General
        await run_ai_analysis(update, context, status_msg, text=text_content, doc_type="general")
        return ConversationHandler.END

    # --- СЦЕНАРИЙ 2: ФАЙЛЫ (PDF / ФОТО) ---
    # Нужно спросить тип документа
    
    # Очищаем временное хранилище
    context.user_data['temp_text'] = ""
    context.user_data['temp_image'] = None
    
    status_msg = await msg.reply_text("📥 Читаю файл...")

    try:
        # Если PDF
        if msg.document and msg.document.mime_type == 'application/pdf':
            file = await msg.document.get_file()
            byte_array = await file.download_as_bytearray()
            # Читаем текст из PDF сразу
            text_from_pdf = extract_text_from_pdf(byte_array)
            context.user_data['temp_text'] = text_from_pdf
            
        # Если ФОТО
        elif msg.photo:
            file = await msg.photo[-1].get_file()
            image_bytes = await file.download_as_bytearray()
            context.user_data['temp_image'] = image_bytes
            # Не забываем про подпись (Caption)
            if msg.caption:
                context.user_data['temp_text'] = msg.caption

        # Показываем кнопки
        keyboard = [
            [InlineKeyboardButton("📄 Statement (Стейтмент)", callback_data="type_statement")],
            [InlineKeyboardButton("⛽ Fuel (Топливо)", callback_data="type_fuel")],
            [InlineKeyboardButton("🧾 Receipt / Other (Чек/Прочее)", callback_data="type_general")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text("📂 Что это за документ?", reply_markup=reply_markup)
        
        # Ждем нажатия кнопки
        return WAITING_FOR_DOC_TYPE

    except Exception as e:
        logging.error(f"Upload Error: {e}")
        await status_msg.edit_text(f"Ошибка чтения файла: {e}")
        return ConversationHandler.END

async def doc_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопок"""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    if choice == "cancel":
        await query.edit_message_text("❌ Отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    # Определяем тип
    doc_type = "general"
    if choice == "type_statement": doc_type = "statement"
    if choice == "type_fuel": doc_type = "fuel"
    
    await query.edit_message_text(f"✅ Выбрано: {doc_type.upper()}. Запускаю AI...")
    
    # Достаем данные из памяти
    text_content = context.user_data.get('temp_text')
    image_bytes = context.user_data.get('temp_image')
    
    # Запускаем анализ
    return await run_ai_analysis(update, context, None, text_content, image_bytes, doc_type, is_callback=True)

async def run_ai_analysis(update, context, status_msg, text=None, image_bytes=None, doc_type="general", is_callback=False):
    """
    Общая функция логики AI и сохранения.
    """
    if is_callback:
        effective_message = update.callback_query.message
    else:
        effective_message = update.message

    try:
        # 1. Запрос к AI с нужным PROMPT (doc_type)
        result = await analyze_content(text, image_bytes, doc_type=doc_type)
        
        # Если ничего не нашли
        if not result or not result.get("items"):
            err_text = "🤷‍♂️ AI не смог извлечь данные."
            if is_callback: await effective_message.reply_text(err_text)
            else: await status_msg.edit_text(err_text)
            return ConversationHandler.END

        # 2. Сохраняем результат временно
        context.user_data['pending_transaction'] = result
        
        # Считаем сумму для красоты
        total_amount = sum(item['amount'] for item in result['items'])
        count_items = len(result['items'])
        
        # 3. Проверяем Дату
        if not result.get("date"):
            # Если даты нет, просим ввести
            ask_text = f"💰 Нашел {count_items} поз. на ${total_amount:.2f}.\n📅 Даты нет в документе. Введи дату (MM.DD):"
            
            if is_callback: await effective_message.reply_text(ask_text)
            else: 
                await status_msg.delete()
                await effective_message.reply_text(ask_text)
                
            return WAITING_FOR_DATE
        
        # 4. Если дата есть — сохраняем
        await execute_save(effective_message, context, result['date'])
        return ConversationHandler.END

    except Exception as e:
        logging.error(f"Analysis Error: {e}")
        if is_callback: await effective_message.reply_text(f"Error: {e}")
        else: await status_msg.edit_text(f"Error: {e}")
        return ConversationHandler.END

async def ask_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Если юзер вводит дату вручную"""
    date_text = update.message.text
    parsed_date = parse_date(date_text)
    date_str = parsed_date.strftime("%m.%d.%Y")
    
    # Сохраняем
    await execute_save(update.message, context, date_str)
    return ConversationHandler.END

async def execute_save(message, context, date_str):
    """Финальная запись в Google Sheets"""
    data = context.user_data.get('pending_transaction')
    
    try:
        # 1. Считаем неделю
        d_obj = parse_date(date_str)
        week_range = get_week_range(d_obj)
        
        # 2. Ищем строку
        ws = get_worksheet()
        row = find_row_by_week(ws, week_range)
        
        if not row:
            await message.reply_text(f"❌ Неделя {week_range} не найдена в таблице.")
            return

        report_lines = []
        items = data.get('items', [])
        
        # 3. Записываем каждую позицию
        for item in items:
            cat = item.get('category', 'other')
            amt = item.get('amount', 0.0)
            desc = item.get('description', 'Bot')
            
            if amt > 0:
                # Маппинг колонки
                col = CATEGORIES_MAP.get(cat, CATEGORIES_MAP['other'])
                # Обновление
                old, new = update_cell_with_note(ws, row, col, amt, desc)
                report_lines.append(f"✅ {cat.upper()}: ${amt} ({desc})")
        
        # Отчет
        if report_lines:
            await message.reply_text(
                f"📅 Неделя: {week_range}\n" + "\n".join(report_lines)
            )
        else:
            await message.reply_text("⚠️ Суммы равны 0, ничего не записал.")
            
        # Чистим память
        context.user_data.clear()

    except Exception as e:
        logging.error(f"Save Error: {e}")
        await message.reply_text(f"Ошибка записи: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена.")
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[
            # Ловим Фото, PDF, Голос, Текст
            MessageHandler(filters.PHOTO | filters.Document.PDF | filters.VOICE | filters.TEXT & ~filters.COMMAND, process_input)
        ],
        states={
            WAITING_FOR_DOC_TYPE: [CallbackQueryHandler(doc_type_callback)],
            WAITING_FOR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # --- ЗАПУСК ДЛЯ CLOUD RUN ---
    PORT = os.environ.get("PORT")
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 

    if PORT and WEBHOOK_URL:
        # Если есть PORT и URL (в облаке)
        print(f"🚀 Starting Webhook on port {PORT}...")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        )
    else:
        # Если нет (локально)
        print("🐢 Starting Polling (Local Mode)...")
        application.run_polling()
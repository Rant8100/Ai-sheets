import json
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID, TAB_NAME, GOOGLE_SA_JSON, DATE_COLUMN
from services.calendar_service import normalize_week_string

def get_worksheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_SA_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(TAB_NAME)

def find_row_by_week(ws, target_week_str: str):
    """Ищет строку, где в колонке B записана нужная неделя."""
    # Получаем все значения колонки дат
    # (Оптимизация: можно кэшировать, но для надежности читаем каждый раз)
    date_col_values = ws.col_values(ord(DATE_COLUMN) - 64) # B -> 2
    
    target_norm = normalize_week_string(target_week_str)
    
    for idx, val in enumerate(date_col_values):
        if normalize_week_string(val) == target_norm:
            return idx + 1 # Gspread row starts at 1
            
    # Если недели нет — создаем новую вверху (после заголовка) или внизу?
    # По ТЗ просто "выбирает неделю". Если её нет — ошибка или создать. 
    # Допустим, мы добавляем новую строку после заголовков (строка 2).
    # Но безопаснее вернуть None и сообщить юзеру.
    return None

def update_cell_with_note(ws, row, col_letter, amount, comment):
    """
    1. Читает текущее значение.
    2. Складывает с новым.
    3. Добавляет запись в Note (Заметку).
    """
    cell_addr = f"{col_letter}{row}"
    
    # Получаем текущее значение и заметку
    # batch_get эффективнее, но для простоты используем простые вызовы
    cell = ws.acell(cell_addr)
    current_val_str = cell.value
    
    try:
        current_val = float(current_val_str.replace(",", "").replace("$", "")) if current_val_str else 0.0
    except:
        current_val = 0.0
        
    new_val = current_val + float(amount)
    
    # Работа с заметкой
    try:
        current_note = ws.get_note(cell_addr)
    except:
        current_note = ""
        
    entry = f"+ ${amount} ({comment})"
    final_note = f"{current_note}\n{entry}" if current_note else entry
    
    # Атомарное обновление (насколько возможно в gspread)
    ws.update(range_name=cell_addr, values=[[new_val]])
    ws.update_note(cell_addr, final_note)
    
    return current_val, new_val
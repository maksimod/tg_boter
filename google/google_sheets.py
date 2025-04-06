import os
import json
import logging
import aiohttp
from typing import Optional, Dict, List, Any

# Глобальная переменная для хранения URL API
_api_url = None

def load_api_key():
    """Загружает URL API для доступа к Google Sheets."""
    global _api_url
    
    # Проверяем наличие ключа в переменных окружения
    api_key = os.environ.get("GOOGLE_SHEETS_API_KEY")
    if api_key and (api_key.startswith("http://") or api_key.startswith("https://")):
        _api_url = api_key
        logging.info(f"API URL загружен из переменных окружения: {_api_url}")
        return True
    
    # Проверяем наличие ключа в файле конфигурации
    try:
        if os.path.exists("credentials/google"):
            # Пытаемся импортировать из модуля
            try:
                from credentials.google.config import API_KEY
                if API_KEY.startswith("http://") or API_KEY.startswith("https://"):
                    _api_url = API_KEY
                    logging.info(f"API URL загружен из credentials/google/config.py: {_api_url}")
                    return True
            except ImportError:
                pass
            
            # Пытаемся прочитать из файла
            try:
                token_path = "credentials/google/key.txt"
                if os.path.exists(token_path):
                    with open(token_path, "r") as f:
                        key = f.read().strip()
                        if key.startswith("http://") or key.startswith("https://"):
                            _api_url = key
                            logging.info(f"API URL загружен из credentials/google/key.txt: {_api_url}")
                            return True
            except Exception as e:
                logging.error(f"Ошибка при чтении API URL из файла: {e}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке API URL: {e}")
    
    logging.warning("API URL для Google Sheets не найден. Функция будет недоступна.")
    return False

async def get_sheets(spreadsheet_id: str, need_sheet: Optional[str] = None) -> Optional[List[List[Any]]]:
    """
    Получает данные из Google Sheets через API.
    
    Args:
        spreadsheet_id: ID таблицы Google Sheets
        need_sheet: Имя листа (необязательно)
        
    Returns:
        Данные из таблицы или None в случае ошибки
    """
    if not _api_url:
        if not load_api_key():
            logging.error("API URL не найден. Невозможно выполнить запрос.")
            return None
    
    try:
        # Настраиваем запрос к API
        data = {
            "spreadsheet_id": spreadsheet_id
        }
        
        # Добавляем need_sheet, если указано
        if need_sheet:
            data["need_sheet"] = need_sheet
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"Отправка запроса к API Google Sheets: {_api_url}")
        print(f"Параметры: spreadsheet_id={spreadsheet_id}, need_sheet={need_sheet}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(_api_url, 
                                  headers=headers, 
                                  json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Ошибка API ({response.status}): {error_text}")
                    return None
                
                # Получаем ответ
                response_text = await response.text()
                print(f"Ответ от API: {response_text[:200]}...")  # Выводим первые 200 символов ответа
                
                try:
                    # Пробуем распарсить JSON
                    result = json.loads(response_text)
                    
                    # Проверяем разные варианты полей в ответе
                    if isinstance(result, list):
                        # Если ответ сразу пришел как список, возвращаем его
                        return result
                    elif isinstance(result, dict):
                        # Ищем данные в различных полях JSON
                        if "data" in result:
                            return result["data"]
                        elif "values" in result:
                            return result["values"]
                        elif "result" in result:
                            return result["result"]
                        elif "rows" in result:
                            return result["rows"]
                        else:
                            # Если не нашли известных полей, возвращаем весь словарь
                            print(f"Неизвестный формат ответа: {result}")
                            return result
                    else:
                        print(f"Неизвестный формат ответа: {result}")
                        return None
                except json.JSONDecodeError:
                    print(f"Не удалось распарсить JSON: {response_text[:100]}...")
                    return None
                    
    except Exception as e:
        print(f"Ошибка при вызове API Google Sheets: {e}")
        return None

# Загружаем API ключ при импорте модуля
load_api_key() 
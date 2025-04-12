import os
import json
import logging
from typing import Optional, Dict, List, Any, Union
import requests

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

def google_sheets(operation: str, sheet_id: str, *args) -> Optional[Any]:
    """
    Универсальная функция для работы с Google Sheets.
    
    Args:
        operation: Тип операции ('get', 'append', 'update', 'delete')
        sheet_id: ID таблицы или листа
        *args: Дополнительные аргументы в зависимости от операции
    
    Returns:
        Результат операции или None в случае ошибки
    """
    if not _api_url:
        if not load_api_key():
            logging.error("API URL не найден. Невозможно выполнить запрос.")
            return None
    
    try:
        # Базовый набор данных для запроса
        data = {
            "operation": operation,
            "sheet_id": sheet_id
        }
        
        # Добавляем дополнительные параметры в зависимости от операции
        if operation == 'get':
            # Для get не требуется дополнительных параметров
            pass
        elif operation == 'append':
            if len(args) < 1:
                raise ValueError("Для операции 'append' требуется словарь данных")
            data["row_data"] = args[0]
        elif operation == 'update':
            if len(args) < 2:
                raise ValueError("Для операции 'update' требуется имя поля для идентификации и словарь данных")
            data["id_field"] = args[0]
            data["row_data"] = args[1]
        elif operation == 'delete':
            if len(args) < 2:
                raise ValueError("Для операции 'delete' требуется номер начальной строки и количество строк")
            data["start_row"] = args[0]
            data["row_count"] = args[1]
        else:
            raise ValueError(f"Неподдерживаемая операция: {operation}")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logging.info(f"Отправка запроса к API Google Sheets: {_api_url}")
        logging.info(f"Операция: {operation}, ID: {sheet_id}")
        
        # Синхронный запрос
        response = requests.post(
            _api_url,
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            logging.error(f"Ошибка API ({response.status_code}): {response.text}")
            return None
        
        # Получаем ответ
        response_text = response.text
        logging.debug(f"Ответ от API: {response_text[:200]}...")  # Выводим первые 200 символов ответа
        
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
                elif "success" in result:
                    return result["success"]
                else:
                    # Если не нашли известных полей, возвращаем весь словарь
                    logging.warning(f"Неизвестный формат ответа: {result}")
                    return result
            else:
                logging.warning(f"Неизвестный формат ответа: {result}")
                return None
        except json.JSONDecodeError:
            logging.error(f"Не удалось распарсить JSON: {response_text[:100]}...")
            return None
                
    except Exception as e:
        logging.error(f"Ошибка при вызове API Google Sheets: {e}")
        return None

async def get_sheets(spreadsheet_id: str, need_sheet: Optional[str] = None) -> Optional[List[List[Any]]]:
    """
    Получает данные из Google Sheets через API (асинхронная версия).
    Оставлена для обратной совместимости.
    
    Args:
        spreadsheet_id: ID таблицы Google Sheets
        need_sheet: Имя листа (необязательно)
        
    Returns:
        Данные из таблицы или None в случае ошибки
    """
    # Прямой вызов синхронной функции
    return google_sheets('get', spreadsheet_id)

# Загружаем API ключ при импорте модуля
load_api_key() 
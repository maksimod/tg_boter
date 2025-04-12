import os
import json
import logging
from typing import Optional, Dict, List, Any, Union
import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Получаем данные сервисного аккаунта
try:
    from credentials.google.config import SERVICE_ACCOUNT_EMAIL, PRIVATE_KEY
    credentials_loaded = True
except ImportError:
    credentials_loaded = False
    logging.error("Не удалось загрузить учетные данные сервисного аккаунта Google")

def get_service():
    """Получает сервис для работы с Google Sheets API."""
    if not credentials_loaded:
        logging.error("Учетные данные сервисного аккаунта не загружены")
        return None

    try:
        # Создаем учетные данные сервисного аккаунта
        credentials = service_account.Credentials.from_service_account_info(
            {
                "type": "service_account",
                "project_id": "engaged-iridium-443819-f2",
                "private_key_id": "private_key_id",
                "private_key": PRIVATE_KEY,
                "client_email": SERVICE_ACCOUNT_EMAIL,
                "client_id": "client_id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{SERVICE_ACCOUNT_EMAIL.replace('@', '%40')}"
            },
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Создаем сервис для работы с Google Sheets API
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        logging.error(f"Ошибка при создании сервиса Google Sheets: {e}")
        return None

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
    service = get_service()
    if not service:
        logging.error("Не удалось создать сервис Google Sheets")
        return None
    
    try:
        # Получаем обработчик Sheets API
        sheets = service.spreadsheets()
        
        # Выполняем операцию в зависимости от типа
        if operation == 'get':
            # Получаем данные из таблицы
            # sheet_id - это ID таблицы
            result = sheets.values().get(
                spreadsheetId=sheet_id,
                range='A1:Z1000'  # Диапазон можно настроить
            ).execute()
            
            # Проверяем наличие данных
            if 'values' in result:
                return result['values']
            else:
                return []
                
        elif operation == 'append':
            if len(args) < 1:
                raise ValueError("Для операции 'append' требуется словарь данных")
            
            row_data = args[0]
            if not isinstance(row_data, dict):
                raise TypeError("Аргумент row_data должен быть словарем")
            
            # Преобразуем словарь в список значений
            # Предполагается, что первая строка таблицы содержит заголовки столбцов
            header_result = sheets.values().get(
                spreadsheetId=sheet_id,
                range='A1:Z1'  # Получаем только первую строку для заголовков
            ).execute()
            
            if 'values' not in header_result or not header_result['values']:
                logging.error("Не удалось получить заголовки таблицы")
                return None
            
            headers = header_result['values'][0]
            
            # Создаем список значений в том же порядке, что и заголовки
            values = []
            for header in headers:
                if header in row_data:
                    # Если значение является списком или словарем, преобразуем его в JSON
                    if isinstance(row_data[header], (dict, list)):
                        values.append(json.dumps(row_data[header]))
                    else:
                        values.append(row_data[header])
                else:
                    values.append("")  # Пустое значение для отсутствующих полей
            
            # Добавляем строку в таблицу
            result = sheets.values().append(
                spreadsheetId=sheet_id,
                range='A1',  # Начинаем с первой ячейки
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={
                    'values': [values]
                }
            ).execute()
            
            return {'success': True, 'result': result}
            
        elif operation == 'update':
            if len(args) < 2:
                raise ValueError("Для операции 'update' требуется имя поля для идентификации и словарь данных")
            
            id_field = args[0]
            row_data = args[1]
            
            if not isinstance(row_data, dict):
                raise TypeError("Аргумент row_data должен быть словарем")
            
            if id_field not in row_data:
                raise ValueError(f"Идентификационное поле {id_field} должно быть в row_data")
            
            # Получаем все данные из таблицы
            result = sheets.values().get(
                spreadsheetId=sheet_id,
                range='A1:Z1000'  # Диапазон можно настроить
            ).execute()
            
            if 'values' not in result or len(result['values']) < 2:
                logging.error("Не удалось получить данные таблицы или таблица пуста")
                return None
            
            headers = result['values'][0]
            data_rows = result['values'][1:]
            
            # Ищем индекс идентификационного поля
            if id_field not in headers:
                raise ValueError(f"Идентификационное поле {id_field} не найдено в заголовках таблицы")
            
            id_index = headers.index(id_field)
            id_value = row_data[id_field]
            
            # Находим строку для обновления
            row_index = None
            for i, row in enumerate(data_rows):
                if len(row) > id_index and str(row[id_index]) == str(id_value):
                    row_index = i + 1  # +1 потому что первая строка - заголовки (индекс 0)
                    break
            
            if row_index is None:
                logging.error(f"Не найдена строка с {id_field}={id_value}")
                return None
            
            # Создаем обновленную строку
            updated_row = []
            for header in headers:
                if header in row_data:
                    # Если значение является списком или словарем, преобразуем его в JSON
                    if isinstance(row_data[header], (dict, list)):
                        updated_row.append(json.dumps(row_data[header]))
                    else:
                        updated_row.append(row_data[header])
                else:
                    # Находим индекс текущего заголовка
                    header_index = headers.index(header)
                    # Используем существующее значение, если оно есть
                    if len(data_rows[row_index - 1]) > header_index:
                        updated_row.append(data_rows[row_index - 1][header_index])
                    else:
                        updated_row.append("")
            
            # Обновляем строку в таблице
            range_to_update = f'A{row_index + 1}:{chr(65 + len(headers) - 1)}{row_index + 1}'
            result = sheets.values().update(
                spreadsheetId=sheet_id,
                range=range_to_update,
                valueInputOption='RAW',
                body={
                    'values': [updated_row]
                }
            ).execute()
            
            return {'success': True, 'result': result}
            
        elif operation == 'delete':
            if len(args) < 2:
                raise ValueError("Для операции 'delete' требуется номер начальной строки и количество строк")
            
            start_row = args[0]
            row_count = args[1]
            
            if not isinstance(start_row, int) or not isinstance(row_count, int):
                raise TypeError("Аргументы start_row и row_count должны быть целыми числами")
            
            # В Google Sheets API для удаления строк нужно использовать batchUpdate
            result = sheets.batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    'requests': [
                        {
                            'deleteDimension': {
                                'range': {
                                    'sheetId': 0,  # ID листа в таблице (обычно 0 для первого листа)
                                    'dimension': 'ROWS',
                                    'startIndex': start_row - 1,  # -1 потому что индексация с 0
                                    'endIndex': start_row - 1 + row_count
                                }
                            }
                        }
                    ]
                }
            ).execute()
            
            return {'success': True, 'result': result}
            
        else:
            raise ValueError(f"Неподдерживаемая операция: {operation}")
            
    except Exception as e:
        logging.error(f"Ошибка при работе с Google Sheets: {e}")
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
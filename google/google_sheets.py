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

def google_sheets(operation: str, spreadsheet_id: str, *args) -> Optional[Any]:
    """
    Универсальная функция для работы с Google Sheets.
    
    Args:
        operation: Тип операции ('get', 'append', 'update', 'delete')
        spreadsheet_id: ID таблицы Google Sheets
        *args: Дополнительные аргументы в зависимости от операции:
            - 'get': нет дополнительных аргументов
            - 'append': sheet_id (ID листа), dict с данными для добавления
            - 'update': sheet_id (ID листа), имя поля для идентификации, dict с данными для обновления
            - 'delete': sheet_id (ID листа), номер начальной строки, количество строк для удаления
    
    Returns:
        Результат операции в формате JSON или None в случае ошибки
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
            try:
                # Получаем метаданные таблицы, чтобы узнать все листы
                spreadsheet = sheets.get(spreadsheetId=spreadsheet_id).execute()
                
                # Получаем все листы из таблицы
                sheet_list = spreadsheet.get('sheets', [])
                
                # Массив всех листов для результата
                final_result = []
                
                for i, sheet in enumerate(sheet_list):
                    sheet_name = sheet['properties']['title']
                    
                    # Получаем данные для текущего листа
                    try:
                        sheet_result = sheets.values().get(
                            spreadsheetId=spreadsheet_id,
                            range=f"'{sheet_name}'!A1:Z1000",
                            valueRenderOption='UNFORMATTED_VALUE',
                            dateTimeRenderOption='FORMATTED_STRING'
                        ).execute()
                    except Exception as e:
                        continue
                    
                    # Список словарей для текущего листа
                    sheet_data = []
                    
                    # Проверяем наличие данных
                    if 'values' in sheet_result and len(sheet_result['values']) > 0:
                        values = sheet_result['values']
                        
                        # Если есть хотя бы заголовки
                        if len(values) > 0:
                            headers = values[0]
                            
                            # Если есть строки данных
                            if len(values) > 1:
                                for row_idx in range(1, len(values)):
                                    row = values[row_idx]
                                    row_dict = {"row_number": row_idx + 1}  # Добавляем номер строки
                                    
                                    # Создаем словарь, где ключи - заголовки, значения - данные
                                    for col_idx in range(min(len(headers), len(row))):
                                        if headers[col_idx]:  # Проверяем, что заголовок не пустой
                                            row_dict[headers[col_idx]] = row[col_idx]
                                    
                                    # Добавляем строку в результат
                                    sheet_data.append(row_dict)
                            else:
                                # Если есть только заголовки, но нет данных - создаем пустой маркер с заголовками
                                empty_dict = {"row_number": 0, "empty_sheet": True}
                                for header in headers:
                                    if header:
                                        empty_dict[header] = ""
                                sheet_data.append(empty_dict)
                    
                    # Добавляем данные этого листа в общий результат, даже если лист пустой
                    if sheet_data:
                        final_result.append(sheet_data)
                    else:
                        # Если в листе совсем нет данных (даже заголовков), создаем пустой маркер
                        final_result.append([{"row_number": 0, "empty_sheet": True}])
                
                # Проверяем, что у нас есть какие-то данные
                if not final_result:
                    return []
                
                # Если есть только один лист, просто возвращаем его данные
                if len(final_result) == 1:
                    return final_result[0]
                
                # Для нескольких листов возвращаем строку с разделителями
                result_string = ""
                for i, sheet_data in enumerate(final_result):
                    if i > 0:
                        result_string += ";"
                    result_string += json.dumps(sheet_data, ensure_ascii=False)
                
                return result_string
                
            except Exception as e:
                logging.error(f"Ошибка при получении данных из Google Sheets: {e}")
                return None
                
        elif operation == 'append':
            if len(args) < 2:
                raise ValueError("Для операции 'append' требуется ID листа и словарь данных")
            
            sheet_id = args[0]  # ID листа
            row_data = args[1]  # Данные для добавления
            
            if not isinstance(row_data, dict):
                raise TypeError("Аргумент row_data должен быть словарем")
            
            # Находим лист по его ID в таблице
            try:
                spreadsheet_info = sheets.get(spreadsheetId=spreadsheet_id).execute()
                sheet_found = False
                sheet_name = None
                
                for sheet in spreadsheet_info.get('sheets', []):
                    if str(sheet['properties']['sheetId']) == str(sheet_id):
                        sheet_name = sheet['properties']['title']
                        sheet_found = True
                        break
                
                if not sheet_found:
                    raise ValueError(f"Лист с ID {sheet_id} не найден в таблице {spreadsheet_id}")
            except Exception as e:
                logging.error(f"Ошибка при поиске листа: {e}")
                return None
            
            # Получаем заголовки из первой строки
            try:
                header_result = sheets.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!A1:Z1"  # Получаем только первую строку для заголовков
                ).execute()
                
                if 'values' not in header_result or not header_result['values']:
                    logging.error("Не удалось получить заголовки таблицы")
                    return None
                
                headers = header_result['values'][0]
            except Exception as e:
                logging.error(f"Ошибка при получении заголовков: {e}")
                return None
            
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
            try:
                result = sheets.values().append(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!A1",  # Начинаем с первой ячейки
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body={
                        'values': [values]
                    }
                ).execute()
                
                return {'success': True, 'result': result}
            except Exception as e:
                logging.error(f"Ошибка при добавлении данных: {e}")
                return None
            
        elif operation == 'update':
            if len(args) < 3:
                raise ValueError("Для операции 'update' требуется ID листа, имя поля для идентификации и словарь данных")
            
            sheet_id = args[0]  # ID листа
            id_field = args[1]  # Поле для идентификации
            row_data = args[2]  # Данные для обновления
            
            if not isinstance(row_data, dict):
                raise TypeError("Аргумент row_data должен быть словарем")
            
            if id_field not in row_data:
                raise ValueError(f"Идентификационное поле {id_field} должно быть в row_data")
            
            # Находим лист по его ID в таблице
            try:
                spreadsheet_info = sheets.get(spreadsheetId=spreadsheet_id).execute()
                sheet_found = False
                sheet_name = None
                
                for sheet in spreadsheet_info.get('sheets', []):
                    if str(sheet['properties']['sheetId']) == str(sheet_id):
                        sheet_name = sheet['properties']['title']
                        sheet_found = True
                        break
                
                if not sheet_found:
                    raise ValueError(f"Лист с ID {sheet_id} не найден в таблице {spreadsheet_id}")
            except Exception as e:
                logging.error(f"Ошибка при поиске листа: {e}")
                return None
            
            # Получаем все данные из листа
            try:
                sheet_result = sheets.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!A1:Z1000"  # Диапазон можно настроить
                ).execute()
                
                if 'values' not in sheet_result or len(sheet_result['values']) < 2:
                    logging.error("Не удалось получить данные таблицы или таблица пуста")
                    return None
                
                headers = sheet_result['values'][0]
                data_rows = sheet_result['values'][1:]
                
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
                range_to_update = f"'{sheet_name}'!A{row_index + 1}:{chr(65 + len(headers) - 1)}{row_index + 1}"
                result = sheets.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_to_update,
                    valueInputOption='RAW',
                    body={
                        'values': [updated_row]
                    }
                ).execute()
                
                return {'success': True, 'result': result}
            except Exception as e:
                logging.error(f"Ошибка при обновлении данных: {e}")
                return None
            
        elif operation == 'delete':
            if len(args) < 3:
                raise ValueError("Для операции 'delete' требуется ID листа, номер начальной строки и количество строк")
            
            sheet_id = args[0]  # ID листа
            start_row = args[1]  # Номер начальной строки
            row_count = args[2]  # Количество строк для удаления
            
            if not isinstance(start_row, int) or not isinstance(row_count, int):
                raise TypeError("Аргументы start_row и row_count должны быть целыми числами")
            
            # Проверяем, существует ли лист с указанным ID
            try:
                spreadsheet_info = sheets.get(spreadsheetId=spreadsheet_id).execute()
                sheet_found = False
                sheet_id_param = None
                
                for sheet in spreadsheet_info.get('sheets', []):
                    if str(sheet['properties']['sheetId']) == str(sheet_id):
                        sheet_id_param = sheet['properties']['sheetId']
                        sheet_found = True
                        break
                
                if not sheet_found:
                    raise ValueError(f"Лист с ID {sheet_id} не найден в таблице {spreadsheet_id}")
                
                # В Google Sheets API для удаления строк нужно использовать batchUpdate
                result = sheets.batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        'requests': [
                            {
                                'deleteDimension': {
                                    'range': {
                                        'sheetId': sheet_id_param,  # ID листа в таблице
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
            except Exception as e:
                logging.error(f"Ошибка при удалении строк: {e}")
                return None
            
        else:
            raise ValueError(f"Неподдерживаемая операция: {operation}")
            
    except Exception as e:
        logging.error(f"Ошибка при работе с Google Sheets: {e}")
        return None

# Оставляем для обратной совместимости
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
    # Прямой вызов синхронной функции с новым интерфейсом
    return google_sheets('get', spreadsheet_id) 
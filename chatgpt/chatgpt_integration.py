import os
import asyncio
import aiohttp
import json
import logging
import re
from functools import wraps
from typing import List, Dict, Any, Optional
from datetime import datetime

# Настройки API ChatGPT
DEFAULT_MODEL = "gpt-3.5-turbo-0125"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000

# Глобальные переменные
_api_key = None
_api_url = None

def load_api_key():
    """Загружает API ключ или URL для локального API."""
    global _api_key, _api_url
    
    # Проверяем наличие ключа в переменных окружения
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        if api_key.startswith("http://") or api_key.startswith("https://"):
            _api_url = api_key
            logging.info(f"Локальный API URL загружен из переменных окружения: {_api_url}")
            return True
        else:
            _api_key = api_key
            logging.info("API ключ OpenAI загружен из переменных окружения")
            return True
    
    # Проверяем наличие ключа в файле конфигурации
    try:
        if os.path.exists("credentials/openai"):
            # Пытаемся импортировать из модуля
            try:
                from credentials.openai.config import API_KEY
                if API_KEY.startswith("http://") or API_KEY.startswith("https://"):
                    _api_url = API_KEY
                    logging.info(f"Локальный API URL загружен из credentials/openai/config.py: {_api_url}")
                    return True
                else:
                    _api_key = API_KEY
                    logging.info("API ключ OpenAI загружен из credentials/openai/config.py")
                    return True
            except ImportError:
                pass
            
            # Пытаемся прочитать из файла
            try:
                token_path = "credentials/openai/key.txt"
                if os.path.exists(token_path):
                    with open(token_path, "r") as f:
                        key = f.read().strip()
                        if key.startswith("http://") or key.startswith("https://"):
                            _api_url = key
                            logging.info(f"Локальный API URL загружен из credentials/openai/key.txt: {_api_url}")
                            return True
                        else:
                            _api_key = key
                            logging.info("API ключ OpenAI загружен из credentials/openai/key.txt")
                            return True
            except Exception as e:
                logging.error(f"Ошибка при чтении API ключа/URL из файла: {e}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке API ключа/URL: {e}")
    
    logging.warning("API ключ/URL не найден. Некоторые функции будут недоступны.")
    return False

async def get_user_messages_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получает историю сообщений пользователя из базы данных.
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество сообщений
        
    Returns:
        Список сообщений пользователя
    """
    try:
        from easy_bot import get_db_connection
        
        conn = await get_db_connection()
        if not conn:
            logging.error("Не удалось получить соединение с БД для истории сообщений")
            return []
        
        # Получаем историю сообщений пользователя
        query = """
            SELECT 
                message_text, 
                is_bot_message,
                created_at
            FROM 
                tgbot_messages 
            WHERE 
                user_id = $1
            ORDER BY 
                created_at DESC
            LIMIT $2
        """
        
        records = await conn.fetch(query, user_id, limit)
        await conn.close()
        
        # Формируем список сообщений в хронологическом порядке (сначала старые)
        messages = []
        for record in reversed(records):
            role = "assistant" if record["is_bot_message"] else "user"
            messages.append({
                "role": role,
                "content": record["message_text"]
            })
        
        return messages
    except Exception as e:
        logging.error(f"Ошибка при получении истории сообщений: {e}")
        return []

async def call_openai_api(messages: List[Dict[str, str]], 
                        model: str = DEFAULT_MODEL,
                        temperature: float = DEFAULT_TEMPERATURE,
                        max_tokens: int = DEFAULT_MAX_TOKENS,
                        language: str = "ru") -> Optional[str]:
    """
    Вызывает API OpenAI или локальный API для получения ответа от модели.
    
    Args:
        messages: Список сообщений для контекста
        model: Название модели OpenAI
        temperature: Температура генерации
        max_tokens: Максимальное количество токенов
        language: Язык ответа
        
    Returns:
        Текст ответа или None в случае ошибки
    """
    if not _api_key and not _api_url:
        if not load_api_key():
            logging.error("API ключ/URL не найден. Невозможно выполнить запрос.")
            return None
    
    # Если используем локальный API
    if _api_url:
        try:
            # Получаем последнее сообщение пользователя (или пустую строку)
            user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
            
            # Получаем системное сообщение (инструкцию)
            system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
            
            # Настраиваем запрос к локальному API
            data = {
                "text": user_message,
                "language": language,
                "prompt": system_message
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            print(f"Отправка запроса к локальному API: {_api_url}")
            
            # Если URL заканчивается на /chatgpt_translate
            endpoint = _api_url
            if not endpoint.endswith("/chatgpt_translate"):
                endpoint = f"{endpoint}/chatgpt_translate"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, 
                                      headers=headers, 
                                      json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Ошибка локального API ({response.status}): {error_text}")
                        return None
                    
                    # Получаем ответ
                    response_text = await response.text()
                    print(f"Ответ от локального API: {response_text}")
                    
                    try:
                        # Пробуем распарсить JSON
                        result = json.loads(response_text)
                        
                        # Если ответ - это словарь
                        if isinstance(result, dict):
                            # Проверяем разные варианты полей
                            if "output" in result:
                                # Декодируем юникод если нужно
                                return decode_unicode_string(result["output"])
                            elif "response" in result:
                                return decode_unicode_string(result["response"])
                            elif "text" in result:
                                return decode_unicode_string(result["text"])
                            elif "content" in result:
                                return decode_unicode_string(result["content"])
                            elif "translated_text" in result:
                                return decode_unicode_string(result["translated_text"])
                            elif "translation" in result:
                                return decode_unicode_string(result["translation"])
                            elif "success" in result and "output" in result:
                                return decode_unicode_string(result["output"])
                            else:
                                # Если нет известных полей, возвращаем весь JSON в виде строки
                                print(f"Неизвестный формат ответа: {result}")
                                # Пробуем найти любое текстовое поле
                                for key, value in result.items():
                                    if isinstance(value, str) and len(value) > 5:
                                        return decode_unicode_string(value)
                                return decode_unicode_string(str(result))
                        elif isinstance(result, str):
                            return decode_unicode_string(result)
                        else:
                            print(f"Неизвестный формат ответа: {result}")
                            return decode_unicode_string(str(result))
                    except json.JSONDecodeError:
                        # Если не удалось распарсить JSON, возвращаем текст как есть
                        print(f"Не удалось распарсить JSON, возвращаем текст как есть: {response_text}")
                        return decode_unicode_string(response_text)
                        
        except Exception as e:
            print(f"Ошибка при вызове локального API: {e}")
            return None
    
    # Если используем официальный API OpenAI
    else:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_api_key}"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                      headers=headers, 
                                      json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"Ошибка API OpenAI ({response.status}): {error_text}")
                        return None
                    
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Ошибка при вызове API OpenAI: {e}")
            return None

def chatgpt(instruction: str):
    """
    Декоратор для интеграции с ChatGPT.
    
    Args:
        instruction: Инструкция для модели ChatGPT
    
    Returns:
        Декоратор для функции
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(message_text, *args, **kwargs):
            from easy_bot import current_update, current_context, auto_write_translated_message
            
            if not current_update or not current_context:
                logging.error("Невозможно получить контекст для ChatGPT")
                return func(message_text, *args, **kwargs)
            
            user_id = current_update.effective_user.id
            chat_id = current_update.effective_chat.id
            
            # Получаем язык пользователя
            user_language = "ru"  # По умолчанию
            if hasattr(current_context, 'user_data') and 'language' in current_context.user_data:
                user_language = current_context.user_data['language']
            
            # Отправляем сообщение о начале обработки запроса
            await current_context.bot.send_message(
                chat_id=chat_id,
                text="⏳ Обрабатываю запрос..."
            )
            
            try:
                # Получаем историю сообщений пользователя
                message_history = await get_user_messages_history(user_id)
                
                # Формируем системную инструкцию с учетом языка
                system_message = {
                    "role": "system",
                    "content": f"""
                    Ты - дружелюбный помощник. Отвечай на {user_language} языке.
                    Инструкция: {instruction}
                    """
                }
                
                # Добавляем текущее сообщение пользователя
                user_message = {
                    "role": "user",
                    "content": message_text
                }
                
                # Создаем сообщения для API
                messages = [system_message] + message_history + [user_message]
                
                # Вызываем API ChatGPT или локальный API
                response = await call_openai_api(messages, language=user_language)
                
                if response:
                    # Отправляем ответ пользователю
                    await current_context.bot.send_message(
                        chat_id=chat_id,
                        text=response
                    )
                    
                    # Добавляем сообщение бота в БД
                    try:
                        await add_message_to_db(user_id, response, is_bot=True)
                    except Exception as e:
                        logging.error(f"Ошибка при добавлении сообщения в БД: {e}")
                else:
                    await current_context.bot.send_message(
                        chat_id=chat_id,
                        text="К сожалению, не удалось получить ответ. Пожалуйста, попробуйте позже."
                    )
            except Exception as e:
                logging.error(f"Ошибка при выполнении запроса к ChatGPT: {e}")
                await current_context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Произошла ошибка: {e}"
                )
            
            return func(message_text, *args, **kwargs)
        
        # Регистрируем обработчик в easy_bot
        try:
            from easy_bot import register_chatgpt_handler
            register_chatgpt_handler(wrapper)
            logging.info("ChatGPT обработчик успешно зарегистрирован")
        except ImportError:
            logging.error("Не удалось импортировать register_chatgpt_handler из easy_bot")
        except Exception as e:
            logging.error(f"Ошибка при регистрации ChatGPT обработчика: {e}")
            
        return wrapper
    return decorator

async def add_message_to_db(user_id: int, message_text: str, is_bot: bool = False):
    """
    Добавляет сообщение в базу данных.
    
    Args:
        user_id: ID пользователя
        message_text: Текст сообщения
        is_bot: Является ли сообщение от бота
    """
    try:
        from easy_bot import get_db_connection
        
        conn = await get_db_connection()
        if not conn:
            logging.error("Не удалось получить соединение с БД для добавления сообщения")
            return
        
        # Получаем ID пользователя в БД
        db_user_id = await conn.fetchval(
            "SELECT id FROM tgbot_users WHERE user_id = $1",
            user_id
        )
        
        if not db_user_id:
            # Создаем запись о пользователе, если еще не существует
            db_user_id = await conn.fetchval(
                "INSERT INTO tgbot_users (user_id, created_at) VALUES ($1, $2) RETURNING id",
                user_id, datetime.now()
            )
        
        # Добавляем сообщение
        await conn.execute(
            """
            INSERT INTO tgbot_messages 
            (user_id, message_text, is_bot_message, created_at) 
            VALUES ($1, $2, $3, $4)
            """,
            db_user_id, message_text, is_bot, datetime.now()
        )
        
        await conn.close()
    except Exception as e:
        logging.error(f"Ошибка при добавлении сообщения в БД: {e}")
        # Не выбрасываем исключение дальше, чтобы не прерывать обработку сообщения

def decode_unicode_string(text):
    """
    Декодирует строку, содержащую Unicode-последовательности вида \\uXXXX.
    
    Args:
        text: Строка для декодирования
        
    Returns:
        Декодированная строка
    """
    if not isinstance(text, str):
        return text
    
    # Если строка не содержит Unicode-последовательностей, возвращаем как есть
    if '\\u' not in text:
        return text
    
    try:
        # Пробуем декодировать через JSON
        decoded = json.loads(f'"{text}"')
        return decoded
    except json.JSONDecodeError:
        # Если не удалось, используем регулярные выражения
        try:
            pattern = '\\\\u([0-9a-fA-F]{4})'
            result = re.sub(pattern, lambda m: chr(int(m.group(1), 16)), text)
            return result
        except Exception as e:
            logging.warning(f"Не удалось декодировать Unicode: {e}")
            return text

# Загружаем API ключ при импорте модуля
load_api_key() 
import os
import asyncio
import aiohttp
import json
import logging
from functools import wraps
from typing import List, Dict, Any, Optional
from datetime import datetime

# Настройки API ChatGPT
DEFAULT_MODEL = "gpt-3.5-turbo-0125"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000

# Глобальные переменные
_api_key = None

def load_api_key():
    """Загружает API ключ OpenAI из конфигурации."""
    global _api_key
    
    # Проверяем наличие ключа в переменных окружения
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        _api_key = api_key
        logging.info("API ключ OpenAI загружен из переменных окружения")
        return True
    
    # Проверяем наличие ключа в файле конфигурации
    try:
        if os.path.exists("credentials/openai"):
            # Пытаемся импортировать из модуля
            try:
                from credentials.openai.config import API_KEY
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
                        _api_key = f.read().strip()
                    logging.info("API ключ OpenAI загружен из credentials/openai/key.txt")
                    return True
            except Exception as e:
                logging.error(f"Ошибка при чтении API ключа OpenAI из файла: {e}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке API ключа OpenAI: {e}")
    
    logging.warning("API ключ OpenAI не найден. Некоторые функции будут недоступны.")
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
                        max_tokens: int = DEFAULT_MAX_TOKENS) -> Optional[str]:
    """
    Вызывает API OpenAI для получения ответа от модели.
    
    Args:
        messages: Список сообщений для контекста
        model: Название модели OpenAI
        temperature: Температура генерации
        max_tokens: Максимальное количество токенов
        
    Returns:
        Текст ответа или None в случае ошибки
    """
    if not _api_key:
        if not load_api_key():
            logging.error("API ключ OpenAI не найден. Невозможно выполнить запрос.")
            return None
    
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
                
                # Вызываем API ChatGPT
                response = await call_openai_api(messages)
                
                if response:
                    # Отправляем ответ пользователю
                    await current_context.bot.send_message(
                        chat_id=chat_id,
                        text=response
                    )
                    
                    # Добавляем сообщение бота в БД
                    await add_message_to_db(user_id, response, is_bot=True)
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
        is_bot: Флаг, является ли сообщение от бота
    """
    try:
        from easy_bot import get_db_connection
        
        conn = await get_db_connection()
        if not conn:
            logging.error("Не удалось получить соединение с БД для сохранения сообщения")
            return
        
        # Добавляем сообщение в БД
        query = """
            INSERT INTO tgbot_messages 
                (user_id, message_text, is_bot_message, created_at) 
            VALUES 
                ($1, $2, $3, $4)
        """
        
        await conn.execute(query, user_id, message_text, is_bot, datetime.now())
        await conn.close()
    except Exception as e:
        logging.error(f"Ошибка при сохранении сообщения в БД: {e}")

# Загружаем API ключ при импорте модуля
load_api_key() 
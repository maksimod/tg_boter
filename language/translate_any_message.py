import os
import logging
import aiohttp
import json
from typing import Optional

# Импортируем конфигурацию OpenAI
try:
    from credentials.openai.config import (
        OPENAI_API_KEY,
        MODEL_NAME,
        TEMPERATURE,
        MAX_TOKENS
    )
    logging.info(f"Загружена конфигурация OpenAI. API ключ {'задан' if OPENAI_API_KEY else 'не задан'}")
except ImportError:
    logging.warning("Не удалось загрузить конфигурацию OpenAI, используем значения по умолчанию")
    # Если конфигурации нет, используем значения по умолчанию
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME = "gpt-3.5-turbo-0125"
    TEMPERATURE = 0.3
    MAX_TOKENS = 1000

# Словарь соответствия языков для translate
LANGUAGE_CODES = {
    "Русский": "ru",
    "Українська": "uk",
    "Украинский": "uk",
    "Английский": "en",
    "English": "en",
    "Китайский": "zh",
    "中文": "zh",
    "Испанский": "es",
    "Español": "es",
    "Французский": "fr",
    "Français": "fr",
    "Немецкий": "de",
    "Итальянский": "it",
    "Японский": "ja",
    "Корейский": "ko",
    "Урду": "ur",
    "اردو": "ur",
    "Хинди": "hi",
    "हिन्दी": "hi",
    "Арабский": "ar",
    "العربية": "ar",
    "Португальский": "pt"
}

# Импортируем функции для работы с БД
from base.database import get_translation_from_db, save_translation_to_db

async def translate_with_translate(text: str, target_language: str) -> Optional[str]:
    """
    Выполняет перевод с помощью библиотеки translate
    
    Args:
        text: Текст для перевода
        target_language: Язык для перевода в понятном человеку формате
        
    Returns:
        Optional[str]: Переведенный текст или None в случае ошибки
    """
    try:
        # Ленивый импорт, чтобы не загружать библиотеку, если она не нужна
        from translate import Translator
        
        # Получаем код языка из понятного человеку названия
        target_lang_code = LANGUAGE_CODES.get(target_language, "en")
        logging.info(f"Используем translate для перевода на {target_language} (код: {target_lang_code})")
        
        translator = Translator(to_lang=target_lang_code, from_lang="ru")
        result = translator.translate(text)
        
        logging.info(f"Перевод через translate выполнен успешно")
        return result
    except Exception as e:
        logging.error(f"Ошибка при переводе через translate: {str(e)}")
        return None

async def translate_any_message(
    message: str, 
    target_language: str,
    source_language: str = "Russian",
    on_translate_start=None,
    on_translate_end=None
) -> Optional[str]:
    """
    Переводит сообщение с языка source_language на язык target_language,
    используя сначала кеш в БД, затем API ChatGPT или библиотеку translate.
    
    Args:
        message: Текст для перевода
        target_language: Язык, на который нужно перевести сообщение
        source_language: Исходный язык сообщения (по умолчанию русский)
        on_translate_start: Опциональный колбэк, вызываемый перед началом перевода
        on_translate_end: Опциональный колбэк, вызываемый после завершения перевода
        
    Returns:
        str: Переведенное сообщение или None в случае ошибки
    """
    if not message:
        logging.debug("Получена пустая строка для перевода")
        return ""
        
    # Перевод не требуется, только если явно указан русский язык
    if target_language.lower() == "русский":
        logging.debug("Перевод не требуется, целевой язык - русский")
        return message
        
    logging.info(f"Начинаем перевод на язык: {target_language}")
    
    # Сначала проверяем наличие перевода в базе данных
    cached_translation = await get_translation_from_db(message, target_language)
    if cached_translation:
        logging.info(f"Найден перевод в базе данных, используем его")
        return cached_translation
    
    # Уведомляем о начале перевода, если предоставлен callback
    if on_translate_start:
        await on_translate_start()
    
    # Пробуем перевести с помощью доступных методов
    translated_text = None
    
    # Сначала пробуем OpenAI, если есть ключ API
    if OPENAI_API_KEY:
        try:
            logging.info(f"Пробуем перевод через OpenAI API")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                
                data = {
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system", 
                            "content": f"You are a professional translator. Translate the following text from {source_language} to {target_language}. Only return the translated text without any explanations or additional information."
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    "temperature": TEMPERATURE,
                    "max_tokens": MAX_TOKENS
                }
                
                logging.debug(f"Отправляем запрос к API OpenAI с моделью {MODEL_NAME}")
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"Ошибка API ChatGPT: {response.status}, {error_text}")
                    else:
                        response_data = await response.json()
                        translated_text = response_data["choices"][0]["message"]["content"].strip()
                        logging.info(f"Перевод через OpenAI выполнен успешно")
                    
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка сети при обращении к API OpenAI: {str(e)}")
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка при разборе ответа OpenAI API: {str(e)}")
        except Exception as e:
            logging.error(f"Неожиданная ошибка при переводе через OpenAI: {str(e)}")
    else:
        logging.warning("OPENAI_API_KEY не задан, пропускаем перевод через OpenAI")
    
    # Если OpenAI не сработал (ошибка или нет ключа), используем translate
    if not translated_text:
        logging.info("Используем запасной вариант для перевода: translate")
        translated_text = await translate_with_translate(message, target_language)
    
    # Если все методы перевода не сработали, возвращаем исходный текст
    if not translated_text:
        logging.warning("Все методы перевода не сработали, возвращаем исходный текст")
        translated_text = message
    
    # Уведомляем о завершении перевода, если предоставлен callback
    if on_translate_end:
        await on_translate_end()
    
    # Сохраняем перевод в базу данных (только если он не равен исходному тексту)
    if translated_text != message:
        await save_translation_to_db(message, translated_text, source_language, target_language)
    
    return translated_text 
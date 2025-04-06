import os
import logging
import aiohttp
import json
from typing import Optional, List, Dict, Any
import asyncio

# Задаем значения по умолчанию
OPENAI_API_KEY = None
MODEL_NAME = "gpt-3.5-turbo-0125"
TEMPERATURE = 0.3
MAX_TOKENS = 1000

# Импортируем конфигурацию OpenAI
try:
    from credentials.openai.config import API_KEY
    OPENAI_API_KEY = API_KEY
    # Отключаем вывод информации о загрузке API ключа
except ImportError:
    # Пробуем получить из переменных окружения
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

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

# Создаем семафор для ограничения одновременных запросов
translation_semaphore = asyncio.Semaphore(5)  # Максимум 5 одновременных переводов

# Семафор для ограничения запросов к базе данных
db_semaphore = asyncio.Semaphore(1)  # Только 1 запрос к БД одновременно

# Кэш в памяти для часто используемых переводов
translation_cache = {}  # {(текст, язык): перевод}

# Импортируем функции для работы с БД
from base.database import get_translation_from_db as get_db_translation
from base.database import save_translation_to_db as save_db_translation

async def get_translation_from_db(source_text: str, target_language: str) -> Optional[str]:
    """
    Получает перевод из базы данных с защитой от одновременного доступа.
    
    Args:
        source_text: Исходный текст
        target_language: Целевой язык
        
    Returns:
        Optional[str]: Переведенный текст или None
    """
    # Проверяем кэш в памяти
    cache_key = (source_text, target_language)
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    # Используем блокировку для доступа к БД
    async with db_semaphore:
        try:
            result = await get_db_translation(source_text, target_language)
            
            # Если нашли перевод, добавляем в кэш в памяти
            if result:
                translation_cache[cache_key] = result
                
            return result
        except Exception as e:
            logging.error(f"Ошибка при получении перевода из БД: {e}")
            return None

async def save_translation_to_db(source_text: str, translated_text: str, 
                               source_language: str, target_language: str) -> None:
    """
    Сохраняет перевод в базу данных с защитой от одновременного доступа.
    
    Args:
        source_text: Исходный текст
        translated_text: Переведенный текст
        source_language: Исходный язык
        target_language: Целевой язык
    """
    # Добавляем в кэш в памяти
    cache_key = (source_text, target_language)
    translation_cache[cache_key] = translated_text
    
    # Не сохраняем в БД очень короткие тексты
    if len(source_text) < 5:
        return
        
    # Используем блокировку для доступа к БД
    async with db_semaphore:
        try:
            await save_db_translation(
                source_text, 
                translated_text, 
                source_language, 
                target_language
            )
        except Exception as e:
            logging.error(f"Ошибка при сохранении перевода в БД: {e}")

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
        
        # Создаем переводчик
        translator = Translator(to_lang=target_lang_code, from_lang="ru")
        result = translator.translate(text)
        
        return result
    except Exception as e:
        # Отключаем логи и только возвращаем None
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
    используя сначала кеш в БД, затем библиотеку translate.
    
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
        return ""
        
    # Перевод не требуется, только если явно указан русский язык
    if target_language.lower() == "русский":
        return message
    
    # Проверяем кэш в памяти
    cache_key = (message, target_language)
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    # Используем семафор для ограничения одновременных запросов на перевод
    async with translation_semaphore:    
        # Сначала проверяем наличие перевода в базе данных
        cached_translation = await get_translation_from_db(message, target_language)
        if cached_translation:
            return cached_translation
        
        # Уведомляем о начале перевода, если предоставлен callback
        if on_translate_start:
            await on_translate_start()
        
        # Пробуем перевести с библиотекой translate
        translated_text = await translate_with_translate(message, target_language)
        
        # Если все методы перевода не сработали, возвращаем исходный текст
        if not translated_text:
            translated_text = message
        
        # Уведомляем о завершении перевода, если предоставлен callback
        if on_translate_end:
            await on_translate_end()
        
        # Сохраняем перевод в базу данных (только если он не равен исходному тексту)
        if translated_text != message:
            await save_translation_to_db(message, translated_text, source_language, target_language)
        
        return translated_text

# Новая функция для параллельного перевода нескольких текстов
async def translate_multiple(texts: List[str], target_language: str, source_language: str = "Russian") -> List[str]:
    """
    Выполняет параллельный перевод списка текстов
    
    Args:
        texts: Список текстов для перевода
        target_language: Целевой язык перевода
        source_language: Исходный язык текстов
        
    Returns:
        List[str]: Список переведенных текстов
    """
    # Перевод не требуется, только если явно указан русский язык
    if target_language.lower() == "русский":
        return texts
    
    # Создаем задачи для всех текстов
    tasks = [
        translate_any_message(
            text, 
            target_language, 
            source_language=source_language,
            on_translate_start=None,
            on_translate_end=None
        ) 
        for text in texts
    ]
    
    # Выполняем все задачи параллельно
    results = await asyncio.gather(*tasks)
    
    return results 
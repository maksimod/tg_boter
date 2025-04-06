import os
import logging
import aiohttp
import json
from typing import Optional

# Задаем значения по умолчанию
OPENAI_API_KEY = None
MODEL_NAME = "gpt-3.5-turbo-0125"
TEMPERATURE = 0.3
MAX_TOKENS = 1000

# Импортируем конфигурацию OpenAI
try:
    from credentials.openai.config import API_KEY
    OPENAI_API_KEY = API_KEY
    logging.info(f"Загружена конфигурация OpenAI. API ключ {'задан' if OPENAI_API_KEY else 'не задан'}")
except ImportError:
    logging.warning("Не удалось загрузить конфигурацию OpenAI, используем значения по умолчанию")
    # Пробуем получить из переменных окружения
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    if OPENAI_API_KEY:
        logging.info("API ключ OpenAI загружен из переменных окружения")
    else:
        logging.warning("API ключ OpenAI не найден ни в конфигурации, ни в переменных окружения")

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
        
        # Отладочный вывод: проверяем переданный язык и код
        print(f"Перевод на язык: {target_language}, код языка: {target_lang_code}")
        
        # Создаем переводчик
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
    
    # ИЗМЕНЕНО: Сразу используем библиотеку translate, пропускаем OpenAI для надежности
    logging.info("Используем библиотеку translate для перевода")
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
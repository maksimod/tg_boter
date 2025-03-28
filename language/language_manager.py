import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Импортируем функцию для перевода сообщений
try:
    from language.translate_any_message import translate_any_message
except ImportError as e:
    logging.error(f"Failed to import translation module: {e}")
    raise

# Languages dictionary
LANGUAGES = {
    "ru": "Русский",
    "uk": "Українська",
    "en": "English",
    "zh": "中文",
    "es": "Español",
    "fr": "Français",
    "ur": "اردو",
    "hi": "हिन्दी",
    "ar": "العربية"
}

# Base messages in Russian (source language)
BASE_MESSAGES = {
    "welcome": "Добро пожаловать! Выберите предпочитаемый язык из доступных вариантов:",
    "language_selected": "Вы выбрали язык: {language}.",
    "main_menu": "Главное меню. Выберите опцию:",
    "option1": "Информация",
    "option2": "Помощь",
    "option3": "О боте",
    "info_text": "Это информационное сообщение.",
    "help_text": "Это справочное сообщение.",
    "about_text": "Это бот с поддержкой нескольких языков: русский, украинский, английский, китайский, испанский, французский, урду, хинди и арабский.",
    "error_message": "Произошла ошибка. Пожалуйста, попробуйте снова с помощью команды /start."
}

async def translate_message(message_key, lang_code):
    """Translate a message from BASE_MESSAGES to the target language"""
    logger = logging.getLogger(__name__)
    
    if message_key not in BASE_MESSAGES:
        logger.warning(f"Message key '{message_key}' not found in BASE_MESSAGES")
        return f"[Missing message: {message_key}]"
    
    source_text = BASE_MESSAGES[message_key]
    target_language = LANGUAGES.get(lang_code, "English")
    
    try:
        translated_text = await translate_any_message(
            source_text, 
            target_language,
            source_language="Russian",
            on_translate_start=None,
            on_translate_end=None
        )
        return translated_text
    except Exception as e:
        logger.error(f"Translation error for key '{message_key}': {str(e)}")
        return source_text

def create_language_keyboard():
    """Create language selection keyboard"""
    keyboard = []
    row = []
    
    for lang_code, lang_name in LANGUAGES.items():
        if len(row) == 2:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(lang_name, callback_data=f"lang_{lang_code}"))
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

async def create_main_menu_keyboard(lang_code):
    """Create main menu keyboard for selected language"""
    option1 = await translate_message("option1", lang_code)
    option2 = await translate_message("option2", lang_code)
    option3 = await translate_message("option3", lang_code)
    
    keyboard = [
        [
            InlineKeyboardButton(option1, callback_data="option_info"),
            InlineKeyboardButton(option2, callback_data="option_help")
        ],
        [
            InlineKeyboardButton(option3, callback_data="option_about")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard) 
"""
Модуль с обработчиками для разговорных взаимодействий с ботом.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler
)

from language.translate_any_message import translate_any_message, LANGUAGE_CODES
from language.language_storage import language_storage
from base.database import get_translation_statistics

logger = logging.getLogger(__name__)

# Состояния диалога
CHOOSING_LANGUAGE, MAIN_MENU, OPTION_SELECTED = range(3)

# Список поддерживаемых языков
SUPPORTED_LANGUAGES = [
    "Русский", "Английский", "Испанский", "Французский", "Немецкий", 
    "Китайский", "Арабский", "Хинди", "Урду"
]

# Базовые сообщения на русском
BASE_MESSAGES = {
    "welcome": "Добро пожаловать! Выберите язык:",
    "language_selected": "Вы выбрали язык: {}.",
    "main_menu": "Главное меню. Выберите опцию:",
    "option1": "Информация",
    "option2": "Помощь",
    "option3": "О боте",
    "info_text": "Это информационное сообщение.",
    "help_text": "Это справочное сообщение.",
    "about_text": "Это бот с поддержкой нескольких языков.",
    "translating": "Выполняется перевод..."
}

async def create_language_keyboard():
    """Создает клавиатуру для выбора языка"""
    keyboard = []
    row = []
    
    for lang in SUPPORTED_LANGUAGES:
        if len(row) == 2:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(lang, callback_data=f"lang_{lang}"))
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

async def translate_and_create_menu_keyboard(target_language):
    """Создает клавиатуру главного меню с переведенными опциями"""
    # Переводим названия кнопок
    option1_text = await translate_any_message(BASE_MESSAGES["option1"], target_language)
    option2_text = await translate_any_message(BASE_MESSAGES["option2"], target_language)
    option3_text = await translate_any_message(BASE_MESSAGES["option3"], target_language)
    
    keyboard = [
        [
            InlineKeyboardButton(option1_text, callback_data="option_info"),
            InlineKeyboardButton(option2_text, callback_data="option_help")
        ],
        [
            InlineKeyboardButton(option3_text, callback_data="option_about")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context) -> int:
    """Обработчик команды /start - показывает выбор языка"""
    logger.info("User triggered /start command")
    
    keyboard = await create_language_keyboard()
    await update.message.reply_text(
        BASE_MESSAGES["welcome"],
        reply_markup=keyboard
    )
    
    return CHOOSING_LANGUAGE

async def language_selected(update: Update, context) -> int:
    """Обрабатывает выбор языка"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем код языка из данных обратного вызова
    selected_language = query.data.replace("lang_", "")
    context.user_data["language"] = selected_language
    
    # Сохраняем выбранный язык в хранилище
    user_id = update.effective_user.id
    language_storage.set_user_language(user_id, selected_language)
    
    # Переводим сообщение о выбранном языке
    language_selected_message = BASE_MESSAGES["language_selected"].format(selected_language)
    translated_message = await translate_any_message(language_selected_message, selected_language)
    
    await query.edit_message_text(
        text=translated_message
    )
    
    # Показываем главное меню
    await show_main_menu(update, context)
    return MAIN_MENU

async def show_main_menu(update: Update, context) -> int:
    """Показывает главное меню для выбранного языка"""
    selected_language = context.user_data.get("language", "Русский")
    
    # Переводим сообщение меню
    menu_message = await translate_any_message(BASE_MESSAGES["main_menu"], selected_language)
    
    # Создаем клавиатуру с переведенными кнопками
    keyboard = await translate_and_create_menu_keyboard(selected_language)
    
    # Разная обработка в зависимости от того, является ли это новым сообщением или обратным вызовом
    if update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=menu_message,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=menu_message,
            reply_markup=keyboard
        )
    
    return MAIN_MENU

async def handle_option(update: Update, context) -> int:
    """Обрабатывает выбор пункта меню"""
    query = update.callback_query
    await query.answer()
    
    option = query.data.replace("option_", "")
    selected_language = context.user_data.get("language", "Русский")
    
    # Выбираем базовое сообщение и переводим его
    if option == "info":
        base_message = BASE_MESSAGES["info_text"]
    elif option == "help":
        base_message = BASE_MESSAGES["help_text"]
    elif option == "about":
        base_message = BASE_MESSAGES["about_text"]
    else:
        base_message = "Option not recognized"
    
    # Создаем переменные для хранения временного сообщения
    temp_message_ref = {"message": None}
    
    # Колбэк для начала перевода
    async def on_start():
        translating_message = await translate_any_message(BASE_MESSAGES["translating"], selected_language)
        temp_message_ref["message"] = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=translating_message
        )
    
    # Колбэк для завершения перевода
    async def on_end():
        if temp_message_ref["message"]:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=temp_message_ref["message"].message_id
            )
    
    # Переводим сообщение с использованием колбэков
    translated_message = await translate_any_message(
        base_message, 
        selected_language,
        on_translate_start=on_start,
        on_translate_end=on_end
    )
    
    await query.edit_message_text(text=translated_message)
    
    # Переводим сообщение меню
    menu_message = await translate_any_message(BASE_MESSAGES["main_menu"], selected_language)
    
    # Создаем клавиатуру с переведенными кнопками
    keyboard = await translate_and_create_menu_keyboard(selected_language)
    
    # Отправляем главное меню снова
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=menu_message,
        reply_markup=keyboard
    )
    
    return MAIN_MENU

async def show_translation_statistics(update: Update, context) -> None:
    """Показывает статистику переводов из базы данных"""
    try:
        stats = await get_translation_statistics()
        if not stats:
            await update.message.reply_text("Статистика переводов пуста или недоступна.")
            return
        
        message = "Статистика переводов:\n\n"
        for item in stats:
            message += f"Язык: {item['target_language']} - {item['count']} переводов\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики переводов: {str(e)}")
        await update.message.reply_text("Не удалось получить статистику переводов.")

def setup_conversation_handler():
    """Настраивает и возвращает обработчик диалогов"""
    # Основной обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_LANGUAGE: [
                CallbackQueryHandler(language_selected, pattern=r'^lang_')
            ],
            MAIN_MENU: [
                CallbackQueryHandler(handle_option, pattern=r'^option_'),
                CommandHandler('menu', show_main_menu)
            ],
            OPTION_SELECTED: [
                CommandHandler('start', start),
                CommandHandler('menu', show_main_menu)
            ]
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    return conv_handler 
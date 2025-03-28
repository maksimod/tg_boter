import logging
import os
import sys
import traceback

print("Starting imports...")

try:
    import signal
    import psutil
    print("Basic imports successful")
except ImportError as e:
    print(f"Error importing basic modules: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from datetime import datetime
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        filters,
        ConversationHandler
    )
    print("Telegram imports successful")
except ImportError as e:
    print(f"Error importing telegram modules: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from credentials.telegram.config import (
        BOT_TOKEN, 
        LOG_LEVEL, 
        LOG_FORMAT, 
        LOG_FILE,
        CONNECTION_POOL_SIZE,
        CONNECT_TIMEOUT,
        READ_TIMEOUT,
        PROXY_URL
    )
    print(f"Loaded Telegram config. BOT_TOKEN exists: {'Yes' if BOT_TOKEN else 'No'}")
except ImportError as e:
    print(f"Error importing telegram config: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

# Setup minimal logging first
try:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logger = logging.getLogger(__name__)
    print("Logging setup successful")
except Exception as e:
    print(f"Error setting up logging: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

# Define states first so the bot can run with minimal functionality even if other imports fail
CHOOSING_LANGUAGE, MAIN_MENU, OPTION_SELECTED = range(3)

# Languages dictionary - simplified for demo
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

# Import translation functionality
try:
    from language.translate_any_message import translate_any_message
    print("Translation module imported successfully")
except ImportError as e:
    print(f"Error importing translation module: {e}")
    traceback.print_exc()
    sys.exit(1)

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

async def error_handler(update, context):
    """Error handler"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    if update and update.effective_chat:
        try:
            # Try to get user's language if available
            lang_code = None
            if context and hasattr(context, 'user_data') and 'language' in context.user_data:
                lang_code = context.user_data['language']
            
            if lang_code:
                # We already have the BASE_MESSAGES dictionary with Russian text
                # So we'll add an error message to it if not exists
                if "error_message" not in BASE_MESSAGES:
                    BASE_MESSAGES["error_message"] = "Произошла ошибка. Пожалуйста, попробуйте снова с помощью команды /start."
                
                translated_error = await translate_message("error_message", lang_code)
                await update.effective_chat.send_message(translated_error)
            else:
                # Fallback to multilingual message
                await update.effective_chat.send_message(
                    "Произошла ошибка / An error occurred / حدث خطأ / एक त्रुटि हुई / ایک خرابی پیش آئی / 发生错误 / Ocurrió un error / Une erreur s'est produite / Сталася помилка. /start"
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}", exc_info=True)
            # Last resort plain message
            await update.effective_chat.send_message(
                "Sorry, an error occurred. Please try again with /start."
            )

# Функция для остановки других экземпляров бота
def kill_other_bot_instances():
    """Останавливает другие экземпляры скрипта бота"""
    try:
        current_pid = os.getpid()
        current_script = sys.argv[0]
        
        logger.info(f"Текущий процесс: {current_pid}, скрипт: {current_script}")
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Проверяем, что это процесс Python и запущен тот же скрипт
                if process.pid != current_pid and 'python' in process.name().lower():
                    cmdline = process.cmdline()
                    if len(cmdline) > 1 and current_script in cmdline[-1]:
                        logger.info(f"Останавливаем процесс бота: {process.pid}")
                        process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.warning(f"Ошибка при проверке процесса {process.pid}: {str(e)}")
                pass
        
        print("Successfully checked for other instances")
    except Exception as e:
        logger.error(f"Ошибка в kill_other_bot_instances: {str(e)}", exc_info=True)
        print(f"Error in kill_other_bot_instances: {str(e)}")
        traceback.print_exc()

async def start(update: Update, context) -> int:
    """Start command handler - shows language selection"""
    logger.info("User triggered /start command")
    
    keyboard = create_language_keyboard()
    
    # Multilingual welcome message
    welcome_message = "Выберите язык / Choose language / اختر لغة / भाषा चुनें / زبان منتخب کریں / 选择语言 / Seleccione idioma / Choisissez la langue / Виберіть мову"
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard
    )
    
    return CHOOSING_LANGUAGE

async def language_selected(update: Update, context) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    # Extract language code from callback data
    lang_code = query.data.replace("lang_", "")
    context.user_data["language"] = lang_code
    
    # Get translated message for selected language
    language_name = LANGUAGES.get(lang_code, "Unknown")
    language_selected_text = await translate_message("language_selected", lang_code)
    language_selected_text = language_selected_text.format(language=language_name)
    
    await query.edit_message_text(
        text=language_selected_text
    )
    
    # Show main menu
    await show_main_menu(update, context)
    return MAIN_MENU

async def show_main_menu(update: Update, context) -> int:
    """Show main menu for selected language"""
    lang_code = context.user_data.get("language", "en")
    main_menu_text = await translate_message("main_menu", lang_code)
    
    keyboard = await create_main_menu_keyboard(lang_code)
    
    # Different handling based on whether this is a new message or callback
    if update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=main_menu_text,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=main_menu_text,
            reply_markup=keyboard
        )
    
    return MAIN_MENU

async def handle_option(update: Update, context) -> int:
    """Handle menu option selection"""
    query = update.callback_query
    await query.answer()
    
    option = query.data.replace("option_", "")
    lang_code = context.user_data.get("language", "en")
    
    # Get translated message based on selected option
    if option == "info":
        message_key = "info_text"
    elif option == "help":
        message_key = "help_text"
    elif option == "about":
        message_key = "about_text"
    else:
        message_key = None
        message = "Option not recognized"
    
    if message_key:
        message = await translate_message(message_key, lang_code)
    
    await query.edit_message_text(text=message)
    
    # Send the main menu again
    main_menu_text = await translate_message("main_menu", lang_code)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=main_menu_text,
        reply_markup=await create_main_menu_keyboard(lang_code)
    )
    
    return MAIN_MENU

def main() -> None:
    """Start the bot."""
    print("=== STARTING BOT ===")
    logger.info("Starting bot...")
    
    # Skip killing other instances as it seems to be problematic
    print("Skipping check for other bot instances...")
    
    print("Building Application...")
    try:
        # Create the Application with custom connection settings
        application_builder = Application.builder().token(BOT_TOKEN)
        
        # Configure connection pool size
        print(f"Setting connection pool size: {CONNECTION_POOL_SIZE}")
        application_builder.connection_pool_size(CONNECTION_POOL_SIZE)
        
        # Configure connection timeouts
        print(f"Setting timeouts: connect={CONNECT_TIMEOUT}, read={READ_TIMEOUT}")
        application_builder.connect_timeout(CONNECT_TIMEOUT)
        application_builder.read_timeout(READ_TIMEOUT)
        
        # Configure proxy if needed
        if PROXY_URL:
            print(f"Using proxy: {PROXY_URL}")
            application_builder.proxy_url(PROXY_URL)
        
        # Build the application
        print("Building application...")
        application = application_builder.build()
        
        # Добавляем обработчик ошибок
        print("Adding error handler...")
        application.add_error_handler(error_handler)
        
        # Сохраняем функцию main_menu в контексте бота для использования в language_handler
        print("Storing main_menu in bot_data...")
        application.bot_data['main_menu_function'] = show_main_menu

        print("Configuring language handler...")
        # Обработчик для выбора языка
        language_handler = ConversationHandler(
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

        # Добавляем обработчики к приложению
        print("Adding handlers to application...")
        application.add_handler(language_handler)

        # Start the Bot with more specific settings
        print("Starting polling...")
        logger.info("Bot is starting up!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)
        print(f"Error in main function: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        # Keep console open to see error
        input("Press Enter to exit...") 
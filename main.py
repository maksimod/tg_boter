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
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch"
}

# Messages dictionary - translations for simple bot messages
MESSAGES = {
    "ru": {
        "welcome": "Добро пожаловать! Выберите язык:",
        "language_selected": "Вы выбрали русский язык.",
        "main_menu": "Главное меню. Выберите опцию:",
        "option1": "Информация",
        "option2": "Помощь",
        "option3": "О боте",
        "info_text": "Это информационное сообщение на русском языке.",
        "help_text": "Это справочное сообщение на русском языке.",
        "about_text": "Это бот с поддержкой нескольких языков."
    },
    "en": {
        "welcome": "Welcome! Please select a language:",
        "language_selected": "You have selected English.",
        "main_menu": "Main menu. Choose an option:",
        "option1": "Information",
        "option2": "Help",
        "option3": "About",
        "info_text": "This is information message in English.",
        "help_text": "This is help message in English.",
        "about_text": "This is a multi-language bot."
    },
    "es": {
        "welcome": "¡Bienvenido! Seleccione un idioma:",
        "language_selected": "Has seleccionado español.",
        "main_menu": "Menú principal. Elige una opción:",
        "option1": "Información",
        "option2": "Ayuda",
        "option3": "Acerca de",
        "info_text": "Este es un mensaje informativo en español.",
        "help_text": "Este es un mensaje de ayuda en español.",
        "about_text": "Este es un bot multilingüe."
    },
    "fr": {
        "welcome": "Bienvenue! Veuillez sélectionner une langue:",
        "language_selected": "Vous avez sélectionné le français.",
        "main_menu": "Menu principal. Choisissez une option:",
        "option1": "Information",
        "option2": "Aide",
        "option3": "À propos",
        "info_text": "Ceci est un message d'information en français.",
        "help_text": "Ceci est un message d'aide en français.",
        "about_text": "C'est un bot multilingue."
    },
    "de": {
        "welcome": "Willkommen! Bitte wählen Sie eine Sprache:",
        "language_selected": "Sie haben Deutsch ausgewählt.",
        "main_menu": "Hauptmenü. Wählen Sie eine Option:",
        "option1": "Information",
        "option2": "Hilfe",
        "option3": "Über",
        "info_text": "Dies ist eine Informationsnachricht auf Deutsch.",
        "help_text": "Dies ist eine Hilfenachricht auf Deutsch.",
        "about_text": "Dies ist ein mehrsprachiger Bot."
    }
}

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

def create_main_menu_keyboard(lang_code):
    """Create main menu keyboard for selected language"""
    messages = MESSAGES.get(lang_code, MESSAGES["en"])
    
    keyboard = [
        [
            InlineKeyboardButton(messages["option1"], callback_data="option_info"),
            InlineKeyboardButton(messages["option2"], callback_data="option_help")
        ],
        [
            InlineKeyboardButton(messages["option3"], callback_data="option_about")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

async def error_handler(update, context):
    """Error handler"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    if update and update.effective_chat:
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
    await update.message.reply_text(
        "Welcome! Please select a language:",
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
    
    # Get messages for selected language
    messages = MESSAGES.get(lang_code, MESSAGES["en"])
    
    await query.edit_message_text(
        text=messages["language_selected"]
    )
    
    # Show main menu
    await show_main_menu(update, context)
    return MAIN_MENU

async def show_main_menu(update: Update, context) -> int:
    """Show main menu for selected language"""
    lang_code = context.user_data.get("language", "en")
    messages = MESSAGES.get(lang_code, MESSAGES["en"])
    
    keyboard = create_main_menu_keyboard(lang_code)
    
    # Different handling based on whether this is a new message or callback
    if update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages["main_menu"],
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=messages["main_menu"],
            reply_markup=keyboard
        )
    
    return MAIN_MENU

async def handle_option(update: Update, context) -> int:
    """Handle menu option selection"""
    query = update.callback_query
    await query.answer()
    
    option = query.data.replace("option_", "")
    lang_code = context.user_data.get("language", "en")
    messages = MESSAGES.get(lang_code, MESSAGES["en"])
    
    # Send response based on selected option
    if option == "info":
        message = messages["info_text"]
    elif option == "help":
        message = messages["help_text"]
    elif option == "about":
        message = messages["about_text"]
    else:
        message = "Option not recognized"
    
    await query.edit_message_text(text=message)
    
    # Send the main menu again
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages["main_menu"],
        reply_markup=create_main_menu_keyboard(lang_code)
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
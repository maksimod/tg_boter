import logging
import sys
import traceback
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler
)

# Импортируем настройки и утилиты
from config.setup import setup_logging, check_dependencies, kill_other_bot_instances
from credentials.telegram.config import (
    BOT_TOKEN, 
    CONNECTION_POOL_SIZE,
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    PROXY_URL
)

# Импортируем обработчики
from handlers.command_handlers import (
    start, 
    language_selected, 
    show_main_menu, 
    handle_option,
    CHOOSING_LANGUAGE, 
    MAIN_MENU, 
    OPTION_SELECTED
)
from handlers.error_handler import error_handler

def main() -> None:
    """Start the bot."""
    print("=== STARTING BOT ===")
    
    # Проверка зависимостей и настройка логирования
    check_dependencies()
    logger = setup_logging()
    logger.info("Starting bot...")
    
    # Skip killing other instances as it seems to be problematic
    print("Skipping check for other bot instances...")
    # Раскомментируйте следующую строку, если нужно остановить другие экземпляры бота
    # kill_other_bot_instances()
    
    try:
        # Create the Application with custom connection settings
        print("Building Application...")
        application_builder = Application.builder().token(BOT_TOKEN)
        
        # Configure connection pool size
        application_builder.connection_pool_size(CONNECTION_POOL_SIZE)
        
        # Configure connection timeouts
        application_builder.connect_timeout(CONNECT_TIMEOUT)
        application_builder.read_timeout(READ_TIMEOUT)
        
        # Configure proxy if needed
        if PROXY_URL:
            application_builder.proxy_url(PROXY_URL)
        
        # Build the application
        application = application_builder.build()
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Сохраняем функцию main_menu в контексте бота для использования в language_handler
        application.bot_data['main_menu_function'] = show_main_menu

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
        application.add_handler(language_handler)

        # Start the Bot with more specific settings
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
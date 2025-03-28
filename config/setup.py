import logging
import os
import sys
import traceback

# Функция для настройки логирования
def setup_logging():
    """Setup logging configuration"""
    try:
        from credentials.telegram.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE
        
        # Use LOG_LEVEL from config if available, otherwise default to INFO
        log_level = getattr(logging, LOG_LEVEL) if hasattr(logging, LOG_LEVEL) else logging.INFO
        
        logging.basicConfig(
            format=LOG_FORMAT if LOG_FORMAT else '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=log_level
        )
        
        # Add console handler
        console = logging.StreamHandler()
        console.setLevel(log_level)
        formatter = logging.Formatter(LOG_FORMAT if LOG_FORMAT else '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        # Add file handler if LOG_FILE is specified
        if LOG_FILE:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logging.getLogger('').addHandler(file_handler)
        
        logger = logging.getLogger(__name__)
        logger.info("Logging setup successful")
        return logger
    except Exception as e:
        print(f"Error setting up logging: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

# Функция для проверки необходимых пакетов
def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import signal
        import psutil
        print("Basic imports successful")
        
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
        
        return True
    except ImportError as e:
        print(f"Error importing modules: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

# Функция для остановки других экземпляров бота
def kill_other_bot_instances():
    """Stops other instances of the bot script"""
    try:
        import psutil
        
        logger = logging.getLogger(__name__)
        current_pid = os.getpid()
        current_script = sys.argv[0]
        
        logger.info(f"Current process: {current_pid}, script: {current_script}")
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check if it's a Python process running the same script
                if process.pid != current_pid and 'python' in process.name().lower():
                    cmdline = process.cmdline()
                    if len(cmdline) > 1 and current_script in cmdline[-1]:
                        logger.info(f"Stopping bot process: {process.pid}")
                        process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.warning(f"Error checking process {process.pid}: {str(e)}")
                pass
        
        print("Successfully checked for other instances")
    except Exception as e:
        logger.error(f"Error in kill_other_bot_instances: {str(e)}", exc_info=True)
        print(f"Error in kill_other_bot_instances: {str(e)}")
        traceback.print_exc() 
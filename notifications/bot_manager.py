"""
Bot management functionality for Telegram notifications bot
"""
import logging
import traceback
from telegram.ext import Application

# Импортируем необходимые функции
from database import init_database
from notifications.core import setup_handlers, start_scheduler, start_bot_polling

# Получаем логгер
logger = logging.getLogger(__name__)

# Глобальный объект для доступа к боту
_bot_app = None

def init_bot(token, run=True):
    """
    Инициализирует и запускает Telegram бота
    
    Args:
        token (str): Токен Telegram бота
        run (bool, optional): Если True, бот запускается автоматически. По умолчанию True.
    
    Returns:
        Application: Объект приложения бота или None в случае ошибки
    """
    global _bot_app
    
    logger.info("Инициализация бота")
    
    if _bot_app is not None:
        logger.info("Бот уже инициализирован, возвращаем существующий экземпляр")
        return _bot_app
    
    if not token:
        logger.error("Токен бота не найден!")
        return None
    
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных для уведомлений...")
        init_database()
        
        # Создание приложения бота
        logger.info("Создание приложения бота с токеном")
        _bot_app = Application.builder().token(token).build()
        
        # Настройка обработчиков команд
        logger.info("Настройка обработчиков команд бота")
        setup_handlers(_bot_app)
        
        # Запуск бота и планировщика в отдельных потоках
        if run:
            logger.info("Запуск бота и планировщика уведомлений")
            scheduler_thread = start_scheduler(_bot_app)
            bot_thread = start_bot_polling(_bot_app)
            logger.info("Бот и планировщик уведомлений успешно запущены")
            logger.info(f"ID потока планировщика: {scheduler_thread.ident}, ID потока бота: {bot_thread.ident}")
        
        return _bot_app
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при инициализации бота: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        return None

def get_bot_app():
    """
    Возвращает текущий экземпляр приложения бота
    
    Returns:
        Application: Объект приложения бота или None, если бот не инициализирован
    """
    global _bot_app
    return _bot_app 
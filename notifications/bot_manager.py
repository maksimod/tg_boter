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
        app = Application.builder().token(token).build()
        
        # Сразу сохраняем экземпляр бота для доступа из процессора уведомлений
        _bot_app = app
        logger.info("Экземпляр бота сохранен глобально и доступен через get_bot_app()")
        
        # Настройка обработчиков команд
        logger.info("Настройка обработчиков команд бота")
        setup_handlers(app)
        
        # Запуск бота и планировщика в отдельных потоках
        if run:
            logger.info("Запуск бота и планировщика уведомлений")
            scheduler_thread = start_scheduler(app)
            bot_thread = start_bot_polling(app)
            logger.info("Бот и планировщик уведомлений успешно запущены")
            logger.info(f"ID потока планировщика: {scheduler_thread.ident}, ID потока бота: {bot_thread.ident}")
        
        return app
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
    if _bot_app is None:
        logger.warning("Попытка получить экземпляр бота, но он еще не инициализирован")
    return _bot_app

def set_bot_app(app):
    """
    Устанавливает внешний экземпляр бота для использования в уведомлениях
    
    Args:
        app: Объект приложения бота telegram.ext.Application
        
    Returns:
        bool: True если успешно установлен, False в противном случае
    """
    global _bot_app
    try:
        if app is None:
            logger.error("Попытка установить None в качестве экземпляра бота")
            return False
            
        # Проверяем, что это действительно объект Application
        if not isinstance(app, Application):
            logger.warning(f"Установлен необычный тип бота: {type(app)}, но продолжаем...")
            
        # Проверяем наличие атрибута bot
        if not hasattr(app, 'bot'):
            logger.error("У переданного объекта отсутствует атрибут 'bot'")
            return False
            
        _bot_app = app
        logger.info(f"Внешний экземпляр бота успешно установлен: {app.bot.username if hasattr(app.bot, 'username') else 'unknown'}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке внешнего экземпляра бота: {e}")
        logger.error(traceback.format_exc())
        return False

# Функция принудительной инициализации бота с заданным токеном
def force_init_bot(token):
    """
    Принудительно инициализирует бота с заданным токеном
    
    Args:
        token (str): Токен Telegram бота
        
    Returns:
        bool: True если инициализация успешна, False в противном случае
    """
    try:
        logger.info("Принудительная инициализация бота")
        app = init_bot(token, run=False)
        return app is not None
    except Exception as e:
        logger.error(f"Ошибка при принудительной инициализации бота: {e}")
        return False 
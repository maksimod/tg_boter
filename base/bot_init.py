import logging
import sys
import traceback

logger = logging.getLogger(__name__)

def initialize_bot():
    """
    Инициализирует и запускает бота с необходимыми настройками.
    
    Returns:
        bool: True если бот успешно запущен, False в противном случае
    """
    try:
        # Получаем экземпляр бота без запуска
        logger.info("Получение экземпляра бота...")
        from easy_bot import get_bot_instance, run_bot
        app = get_bot_instance()
        
        if app is None:
            logger.error("Не удалось получить экземпляр бота")
            return False
        
        # Передаем экземпляр бота в модуль уведомлений
        logger.info("Передача экземпляра бота в модуль уведомлений...")
        try:
            from notifications.bot_manager import set_bot_app
            if set_bot_app(app):
                logger.info("Экземпляр бота успешно передан в модуль уведомлений")
            else:
                logger.error("Не удалось передать экземпляр бота в модуль уведомлений")
        except Exception as e:
            logger.error(f"Ошибка при передаче экземпляра бота: {e}")
            logger.error(traceback.format_exc())
        
        # Теперь запускаем бота
        logger.info("Запуск основного бота...")
        run_bot()
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(traceback.format_exc())
        return False 
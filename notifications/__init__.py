"""
Notifications package for Telegram bot.
This package provides functionality for creating, managing, and sending notifications.
"""
import threading
import logging
import asyncio
import os
import time
from base.db import init_database

# Настройка логирования для пакета уведомлений
logger = logging.getLogger('notifications')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('log/notifications.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

logger.info("Инициализация модуля уведомлений")

# Инициализируем базу данных при импорте модуля
try:
    logger.info("Автоматическая инициализация базы данных при импорте модуля")
    init_database()
    logger.info("База данных успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка при инициализации базы данных: {e}")
    import traceback
    logger.error(traceback.format_exc())

# Export scheduler functions from sender module 
from notifications.sender import check_notifications, scheduled_job, fix_timezones

# Export reminder management functions
from notifications.reminders import create_reminder, get_reminders

# Export notification parsing functions
from notifications.notification_parser import process_notification_request

# Export notification manager functions
from notifications.notification_manager import create_notification

# Export bot management functions
from notifications.bot_manager import init_bot, get_bot_app

# Export notification processor management
from notifications.processor_manager import start_processor, check_processor_running

# Глобальная переменная для отслеживания запущенного процессора
_notification_processor_thread = None

# Функция для запуска процессора уведомлений
def _run_notifications_processor():
    """Внутренняя функция для запуска процессора уведомлений в отдельном потоке"""
    global _notification_processor_thread
    
    # Проверяем, не запущен ли уже процессор
    if _notification_processor_thread is not None and _notification_processor_thread.is_alive():
        logger.info("Процессор уведомлений уже запущен")
        return
    
    # Класс для хранения контекста бота
    class NotificationContext:
        def __init__(self, bot):
            self.bot = bot
    
    # Функция для запуска в отдельном потоке
    def processor_thread():
        logger.info("Запуск процессора уведомлений в отдельном потоке")
        
        # Создаем новый цикл событий для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_processor():
            # Ждем полной инициализации бота с повторными попытками
            app = None
            max_attempts = 30  # 30 попыток с интервалом 2 секунды = до 1 минуты
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Пытаемся получить бота от bot_manager
                    from notifications.bot_manager import get_bot_app
                    app = get_bot_app()
                    
                    if app and hasattr(app, 'bot') and app.bot:
                        logger.info(f"Успешно получен бот для отправки уведомлений (попытка {attempt}): {app.bot.username}")
                        break
                    else:
                        logger.warning(f"Попытка {attempt}/{max_attempts}: Бот еще не инициализирован полностью")
                        await asyncio.sleep(2)  # Ждем 2 секунды между попытками
                except Exception as e:
                    logger.error(f"Ошибка при получении бота (попытка {attempt}): {e}")
                    await asyncio.sleep(2)
            
            # Если все попытки не удались
            if not app or not hasattr(app, 'bot') or not app.bot:
                logger.error(f"Не удалось получить объект бота после {max_attempts} попыток. Процессор уведомлений не запущен.")
                return
            
            # Создаем контекст для отправки уведомлений
            context = NotificationContext(app.bot)
            logger.info(f"Создан контекст для отправки уведомлений с ботом {app.bot.username}")
            
            try:
                # Запускаем немедленную проверку уведомлений
                logger.info("Запуск немедленной проверки уведомлений")
                await check_notifications(context)
                
                # Запускаем регулярную проверку
                logger.info("Запуск регулярной проверки уведомлений")
                await scheduled_job(context)
            except Exception as e:
                logger.error(f"Ошибка при запуске процессора уведомлений: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        try:
            loop.run_until_complete(run_processor())
        except Exception as e:
            logger.error(f"Ошибка в цикле событий процессора уведомлений: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            loop.close()
            logger.info("Цикл событий процессора уведомлений завершен")
    
    # Запускаем процессор в отдельном потоке
    _notification_processor_thread = threading.Thread(target=processor_thread, daemon=True)
    _notification_processor_thread.start()
    logger.info(f"Поток процессора уведомлений запущен с ID: {_notification_processor_thread.ident}")

# Если это основной модуль приложения, запускаем процессор
from threading import Timer
def _delayed_start_processor():
    """Запускает процессор уведомлений с небольшой задержкой после запуска приложения"""
    logger.info("Запланирован отложенный запуск процессора уведомлений (15 сек)")
    Timer(15.0, _run_notifications_processor).start()

# Запускаем процессор с задержкой, чтобы все успело инициализироваться
_delayed_start_processor()

# Экспортируем функцию запуска процессора для явного вызова при необходимости
__all__ = [
    'process_notification_request', 'create_reminder', 'get_reminders',
    'check_notifications', 'scheduled_job', 'fix_timezones',
    'init_bot', 'get_bot_app', 'start_processor', 'check_processor_running',
    'create_notification'
] 
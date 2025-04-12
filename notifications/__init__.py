"""
Notifications package for Telegram bot.
This package provides functionality for creating, managing, and sending notifications.
"""
import threading
import asyncio
import os
import time
from base.db import init_database

# Инициализируем базу данных при импорте модуля
try:
    init_database()
except Exception as e:
    import traceback

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
        return
    
    # Класс для хранения контекста бота
    class NotificationContext:
        def __init__(self, bot):
            self.bot = bot
    
    # Функция для запуска в отдельном потоке
    def processor_thread():
        
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
                        break
                    else:
                        await asyncio.sleep(2)  # Ждем 2 секунды между попытками
                except Exception as e:
                    await asyncio.sleep(2)
            
            # Если все попытки не удались
            if not app or not hasattr(app, 'bot') or not app.bot:
                return
            
            # Создаем контекст для отправки уведомлений
            context = NotificationContext(app.bot)
            
            try:
                # Запускаем немедленную проверку уведомлений
                await check_notifications(context)
                
                # Запускаем регулярную проверку
                await scheduled_job(context)
            except Exception as e:
                import traceback
        
        try:
            loop.run_until_complete(run_processor())
        except Exception as e:
            import traceback
        finally:
            loop.close()
    
    # Запускаем процессор в отдельном потоке
    _notification_processor_thread = threading.Thread(target=processor_thread, daemon=True)
    _notification_processor_thread.start()

# Если это основной модуль приложения, запускаем процессор
from threading import Timer
def _delayed_start_processor():
    """Запускает процессор уведомлений с небольшой задержкой после запуска приложения"""
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
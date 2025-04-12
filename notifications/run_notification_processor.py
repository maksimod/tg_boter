#!/usr/bin/env python
"""
Processor that checks for notifications and sends them.
"""
import os
import sys
import asyncio
import traceback
import time
import pytz
from datetime import datetime

# Настройка пути для импорта модулей из родительской директории
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Импортируем необходимые компоненты
try:
    # Инициализируем базу данных сразу
    from base.db import MOSCOW_TZ, init_database
    
    # Явно инициализируем базу данных
    init_database()
    
    # Импортируем основные модули 
    from notifications.sender import scheduled_job, check_notifications
    from notifications.bot_manager import init_bot, get_bot_app
    
except Exception as e:
    sys.exit(1)

class NotificationContext:
    """
    Контекст для процессора уведомлений.
    """
    def __init__(self, bot):
        self.bot = bot

async def run_notification_processor():
    """
    Основная функция для запуска процессора уведомлений.
    """
    # Печатаем время и временную зону для отладки
    now = datetime.now(MOSCOW_TZ)
    
    try:
        # Инициализация Telegram бота
        
        # Загружаем токен
        token = None
        try:
            from credentials.telegram.config import BOT_TOKEN
            token = BOT_TOKEN
        except Exception as token_error:
            pass
        
        # Инициализируем бота с повторными попытками
        bot_app = None
        max_retries = 5
        retry_count = 0
        
        while bot_app is None and retry_count < max_retries:
            retry_count += 1
            
            try:
                # Пробуем инициализировать бота
                bot_app = init_bot(token, run=False)
                
                if not bot_app:
                    bot_app = get_bot_app()
                
            except Exception as bot_error:
                wait_time = 10  # секунд
                await asyncio.sleep(wait_time)
        
        if not bot_app:
            return
        
        if not hasattr(bot_app, 'bot') or not bot_app.bot:
            return
        
        # Создаем контекст для отправки уведомлений
        context = NotificationContext(bot_app.bot)
        
        # Проверяем уведомления сразу после запуска
        try:
            await check_notifications(context)
        except Exception as immediate_check_error:
            pass
        
        # Запускаем проверку и отправку уведомлений в цикле
        await scheduled_job(context)
        
    except Exception as e:
        pass

if __name__ == "__main__":
    # Создаем файл-маркер для определения, что процессор запущен
    with open("log/notification_processor_running.txt", "w") as f:
        f.write(f"Started at {datetime.now()}")
    
    try:
        # Запускаем асинхронную функцию
        asyncio.run(run_notification_processor())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass
    finally:
        # Удаляем файл-маркер
        try:
            if os.path.exists("log/notification_processor_running.txt"):
                os.remove("log/notification_processor_running.txt")
        except:
            pass 
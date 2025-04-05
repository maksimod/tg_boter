#!/usr/bin/env python
"""
Processor that checks for notifications and sends them.
"""
import os
import sys
import asyncio
import traceback
import logging
import time
import pytz
from datetime import datetime

# Настройка пути для импорта модулей из родительской директории
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log/notifications_processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('notification_processor')
logger.setLevel(logging.DEBUG)

# Импортируем необходимые компоненты
try:
    # Инициализируем базу данных сразу
    from database import MOSCOW_TZ, init_database
    
    # Явно инициализируем базу данных
    logger.info("Инициализация базы данных...")
    init_database()
    logger.info("База данных инициализирована")
    
    # Импортируем основные модули 
    from notifications.sender import scheduled_job, check_notifications
    from notifications.bot_manager import init_bot, get_bot_app
    
    logger.info("Все необходимые модули импортированы успешно")
except Exception as e:
    logger.error(f"Ошибка при импорте модулей: {e}")
    logger.error(traceback.format_exc())
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
    logger.info("===============================================")
    logger.info("ЗАПУСК ПРОЦЕССОРА УВЕДОМЛЕНИЙ")
    logger.info("===============================================")
    
    # Печатаем время и временную зону для отладки
    now = datetime.now(MOSCOW_TZ)
    logger.info(f"Текущее серверное время: {now.strftime('%d.%m.%Y %H:%M:%S %Z%z')}")
    logger.info(f"Используемая временная зона: {MOSCOW_TZ}")
    
    try:
        # Инициализация Telegram бота
        logger.info("Инициализация бота...")
        
        # Загружаем токен
        token = None
        try:
            from credentials.telegram.config import BOT_TOKEN
            token = BOT_TOKEN
            logger.info("Токен бота загружен из конфигурации")
        except Exception as token_error:
            logger.error(f"Ошибка при загрузке токена: {token_error}")
            logger.info("Попытка получить токен другим способом...")
        
        # Инициализируем бота с повторными попытками
        bot_app = None
        max_retries = 5
        retry_count = 0
        
        while bot_app is None and retry_count < max_retries:
            retry_count += 1
            logger.info(f"Попытка {retry_count}/{max_retries} инициализации бота")
            
            try:
                # Пробуем инициализировать бота
                bot_app = init_bot(token, run=False)
                
                if bot_app:
                    logger.info(f"Бот успешно инициализирован через init_bot")
                else:
                    logger.warning("Бот не инициализирован через init_bot, пробуем получить существующий")
                    bot_app = get_bot_app()
                    
                    if bot_app:
                        logger.info("Получен существующий бот")
                    else:
                        logger.error("Не удалось получить существующий бот")
                
            except Exception as bot_error:
                logger.error(f"Ошибка при инициализации бота: {bot_error}")
                logger.error(traceback.format_exc())
            
            if bot_app is None:
                wait_time = 10  # секунд
                logger.info(f"Ожидание {wait_time} секунд перед следующей попыткой...")
                await asyncio.sleep(wait_time)
        
        if not bot_app:
            logger.critical("Не удалось инициализировать бота после всех попыток")
            return
        
        if not hasattr(bot_app, 'bot') or not bot_app.bot:
            logger.critical("Объект бота не содержит атрибут 'bot'")
            return
        
        logger.info(f"Бот успешно инициализирован: {bot_app.bot.username}")
        
        # Создаем контекст для отправки уведомлений
        context = NotificationContext(bot_app.bot)
        logger.info("Создан контекст для обработки уведомлений")
        
        # Проверяем уведомления сразу после запуска
        logger.info("ЗАПУСК НЕМЕДЛЕННОЙ ПРОВЕРКИ УВЕДОМЛЕНИЙ...")
        try:
            await check_notifications(context)
            logger.info("Немедленная проверка уведомлений завершена")
        except Exception as immediate_check_error:
            logger.error(f"Ошибка при немедленной проверке уведомлений: {immediate_check_error}")
            logger.error(traceback.format_exc())
        
        # Запускаем проверку и отправку уведомлений в цикле
        logger.info("Запуск планировщика уведомлений...")
        await scheduled_job(context)
        
    except Exception as e:
        logger.critical(f"Критическая ошибка в процессоре уведомлений: {e}")
        logger.critical(traceback.format_exc())
    
    logger.critical("Процессор уведомлений остановлен!")

if __name__ == "__main__":
    # Создаем файл-маркер для определения, что процессор запущен
    with open("log/notification_processor_running.txt", "w") as f:
        f.write(f"Started at {datetime.now()}")
    
    logger.info("Запуск скрипта процессора уведомлений")
    logger.info(f"PID процесса: {os.getpid()}")
    
    try:
        # Запускаем асинхронную функцию
        asyncio.run(run_notification_processor())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки. Процессор уведомлений завершает работу.")
    except Exception as e:
        logger.critical(f"Необработанная ошибка: {e}")
        logger.critical(traceback.format_exc())
    finally:
        # Удаляем файл-маркер
        try:
            if os.path.exists("log/notification_processor_running.txt"):
                os.remove("log/notification_processor_running.txt")
        except:
            pass
    
    logger.info("Скрипт процессора уведомлений завершил работу") 
"""
Скрипт для запуска процессора уведомлений отдельно от бота
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
import traceback
import time

# Настройка логирования
logger = logging.getLogger('notification_processor')
logger.setLevel(logging.DEBUG)

# Обработчик для файла
file_handler = logging.FileHandler('notifications_processor.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Обработчик для консоли
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Также настроим корневой логгер
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
logger.info("Логирование настроено для процессора уведомлений")

# Добавляем текущую директорию в путь поиска модулей, если ещё не добавлена
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
    logger.info(f"Добавлена директория {current_dir} в путь поиска модулей")

# Импортируем необходимые модули
try:
    from notifications.sender import check_notifications, fix_timezones, scheduled_job
    from notifications.bot_manager import get_bot_app, init_bot
    logger.info("Модули notifications.sender и notifications.bot_manager успешно импортированы")
except Exception as e:
    error_traceback = traceback.format_exc()
    logger.error(f"Ошибка при импорте модулей: {e}")
    logger.error(f"Трассировка ошибки: {error_traceback}")

class NotificationContext:
    """
    Простой класс-заглушка для имитации контекста бота
    """
    def __init__(self, bot):
        self.bot = bot

async def run_notification_processor():
    """
    Основная функция для запуска процессора уведомлений
    """
    logger.info("Запуск процессора уведомлений")
    
    try:
        # Сначала инициализируем бота
        logger.info("Инициализация бота...")
        
        # Попробуем импортировать токен напрямую
        try:
            from credentials.telegram.config import BOT_TOKEN
            logger.info("Токен бота успешно загружен из конфигурации")
        except Exception as token_err:
            logger.error(f"Ошибка при загрузке токена бота: {token_err}")
            logger.info("Попытка запуска без явного указания токена...")
            BOT_TOKEN = None
        
        # Инициализируем бота
        bot_app = None
        max_attempts = 3
        current_attempt = 0
        
        while bot_app is None and current_attempt < max_attempts:
            current_attempt += 1
            logger.info(f"Попытка {current_attempt}/{max_attempts} инициализации бота")
            
            try:
                bot_app = init_bot(BOT_TOKEN, run=False)
                if bot_app:
                    logger.info(f"Бот успешно инициализирован через init_bot: {bot_app}")
                else:
                    logger.warning("Не удалось инициализировать бота через init_bot")
                    
                    # Пробуем получить существующее приложение
                    logger.info("Попытка получить существующее приложение бота...")
                    bot_app = get_bot_app()
                    
                    if bot_app:
                        logger.info(f"Успешно получено существующее приложение бота: {bot_app}")
                    else:
                        logger.error("Не удалось получить существующее приложение бота")
            except Exception as init_error:
                logger.error(f"Ошибка при инициализации бота: {init_error}")
                logger.error(f"Трассировка: {traceback.format_exc()}")
            
            if bot_app is None and current_attempt < max_attempts:
                wait_time = 30  # секунд
                logger.info(f"Ожидание {wait_time} секунд перед следующей попыткой...")
                await asyncio.sleep(wait_time)
            
        if not bot_app:
            logger.error("Не удалось инициализировать бота после всех попыток. Завершение работы процессора.")
            return
            
        # Проверяем наличие бота в приложении
        if not hasattr(bot_app, 'bot') or bot_app.bot is None:
            logger.error("Критическая ошибка: в приложении отсутствует объект бота (bot_app.bot is None)")
            return
            
        logger.info(f"Инициализирован бот: {bot_app.bot}")
        
        # Создаем контекст с ботом для отправки уведомлений
        context = NotificationContext(bot_app.bot)
        logger.info(f"Контекст для отправки уведомлений создан с ботом: {context.bot}")
        
        # Проверка контекста перед запуском
        if not hasattr(context, 'bot') or context.bot is None:
            logger.error("Критическая ошибка: context.bot отсутствует или равен None")
            return
        
        # Исправляем часовые пояса существующих уведомлений перед запуском
        logger.info("Исправление часовых поясов уведомлений...")
        try:
            await fix_timezones()
            logger.info("Часовые пояса уведомлений исправлены")
        except Exception as tz_error:
            logger.error(f"Ошибка при исправлении часовых поясов: {tz_error}")
            logger.error(f"Трассировка: {traceback.format_exc()}")
        
        # Тестовое логирование активных уведомлений
        try:
            from database import get_all_active_notifications
            notifications = get_all_active_notifications()
            logger.info(f"Найдено {len(notifications)} активных уведомлений в базе данных")
            if notifications:
                for n in notifications:
                    logger.info(f"Активное уведомление: ID={n[0]}, user_id={n[1]}, текст='{n[2]}', время={n[3]}, отправлено={n[4]}")
        except Exception as db_error:
            logger.error(f"Ошибка при получении активных уведомлений из БД: {db_error}")
        
        # Запускаем бесконечный цикл проверки уведомлений
        logger.info("Запуск планировщика уведомлений")
        try:
            # Вместо цикла с фиксированной задержкой используем scheduled_job
            await scheduled_job(context)
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Ошибка при выполнении планировщика уведомлений: {e}")
            logger.error(f"Трассировка ошибки: {error_traceback}")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Критическая ошибка в процессоре уведомлений: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
    
    logger.error("Процессор уведомлений остановлен!")

if __name__ == "__main__":
    # Дадим основному приложению время инициализироваться
    logger.info("Ожидание 10 секунд перед запуском процессора...")
    time.sleep(10)
    
    try:
        logger.info("Запуск асинхронного цикла для процессора уведомлений")
        asyncio.run(run_notification_processor())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки. Процессор уведомлений завершает работу.")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Неперехваченная ошибка при запуске процессора уведомлений: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
    
    logger.info("Программа завершена.") 
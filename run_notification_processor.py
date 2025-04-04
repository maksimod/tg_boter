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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notifications_processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('notification_processor')

# Добавляем текущую директорию в путь поиска модулей, если ещё не добавлена
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
    logger.info(f"Добавлена директория {current_dir} в путь поиска модулей")

# Импортируем необходимые модули
try:
    from notifications.sender import check_notifications, fix_timezones
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
        bot_app = init_bot(BOT_TOKEN, run=False)
        if not bot_app:
            logger.error("Не удалось инициализировать бота через init_bot")
            
            # Попробуем получить существующее приложение
            logger.info("Попытка получить существующее приложение бота...")
            bot_app = get_bot_app()
            
        if not bot_app:
            logger.error("Не удалось получить приложение бота. Ожидание 30 секунд для повторной попытки...")
            # Ждем некоторое время, возможно, бот еще не инициализирован основным приложением
            await asyncio.sleep(30)
            
            # Повторная попытка
            logger.info("Повторная попытка получить приложение бота...")
            bot_app = get_bot_app()
            
        if not bot_app:
            logger.error("Не удалось получить приложение бота после повторной попытки. Завершение работы процессора.")
            return
            
        logger.info(f"Бот успешно инициализирован: {bot_app}")
        
        # Создаем контекст с ботом для отправки уведомлений
        context = NotificationContext(bot_app.bot)
        logger.info(f"Контекст для отправки уведомлений создан с ботом: {context.bot}")
        
        # Исправляем часовые пояса существующих уведомлений перед запуском
        logger.info("Исправление часовых поясов уведомлений...")
        try:
            await fix_timezones()
            logger.info("Часовые пояса уведомлений исправлены")
        except Exception as tz_error:
            logger.error(f"Ошибка при исправлении часовых поясов: {tz_error}")
        
        # Запускаем бесконечный цикл проверки уведомлений
        iteration = 0
        
        logger.info("Запуск цикла проверки уведомлений")
        while True:
            iteration += 1
            try:
                # Запускаем проверку уведомлений
                logger.info(f"Итерация #{iteration}: начало проверки уведомлений")
                await check_notifications(context)
                logger.info(f"Итерация #{iteration}: завершение проверки уведомлений")
                
                # Ждем 60 секунд до следующей проверки
                logger.info(f"Итерация #{iteration}: ожидание 60 секунд до следующей проверки")
                await asyncio.sleep(60)
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка в процессоре уведомлений на итерации #{iteration}: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
                # Продолжаем работу даже при ошибке, но с задержкой
                logger.info("Процессор продолжит работу через 60 секунд")
                await asyncio.sleep(60)
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
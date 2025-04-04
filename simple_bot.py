import time
from utils.logger import setup_logging
from credentials.telegram.config import BOT_TOKEN
from notifications import create_reminder, get_reminders
from notifications.bot_manager import init_bot as init_bot_impl

# Настраиваем логирование
logger = setup_logging()

# Функция для инициализации бота
def init_bot(token=None, run=True):
    # Используем токен из конфигурации, если не указан явно
    if token is None:
        token = BOT_TOKEN
    
    # Вызываем функцию инициализации из модуля notifications
    return init_bot_impl(token, run)

# Основная функция для запуска бота напрямую
def main():
    """
    Функция для запуска бота напрямую
    """
    logger.info("Запуск бота напрямую через функцию main()")
    bot = init_bot()
    
    if not bot:
        logger.error("Не удалось инициализировать бота, завершение работы")
        return
    
    # Ожидаем ввод от пользователя для завершения
    print("Бот запущен! Нажмите Ctrl+C для остановки...")
    logger.info("Бот запущен и ожидает сообщений")
    
    try:
        # Бесконечный цикл чтобы бот продолжал работать
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt, завершение работы")
        print("Бот остановлен!")

if __name__ == "__main__":
    main() 
"""
Logging utility functions for the bot application
"""
import logging
import sys

def setup_logging(log_file='simple_bot.log'):
    """
    Настраивает логирование для всего приложения
    
    Args:
        log_file (str): Имя файла для записи логов
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Форматирование логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Обработчик для вывода в файл
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики к корневому логгеру если их еще нет
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Логируем запуск логирования
    root_logger.info("Логирование настроено")
    return root_logger 
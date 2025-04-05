"""
Модуль для управления процессором уведомлений.
Содержит функции для запуска и проверки статуса процессора.
"""
import os
import sys
import subprocess
import logging
import threading
import time

# Настройка логирования
logger = logging.getLogger('notification_manager')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

# Имя скрипта процессора уведомлений
PROCESSOR_SCRIPT = 'run_notification_processor.py'

def start_processor(visible=False):
    """
    Запускает процессор уведомлений в отдельном процессе.
    
    Args:
        visible (bool): Если True, процессор будет запущен с видимой консолью.
        
    Returns:
        bool: True если процессор успешно запущен, False в противном случае.
    """
    logger.info("Запуск процессора уведомлений")
    
    try:
        # Проверяем существование файла запуска
        if not os.path.exists(PROCESSOR_SCRIPT):
            logger.error(f"Файл {PROCESSOR_SCRIPT} не найден")
            return False
            
        # Проверяем, не запущен ли уже процессор уведомлений
        if check_processor_running():
            logger.info("Процессор уведомлений уже запущен")
            return True
        
        # Определяем параметры запуска
        if visible:
            # Запуск с видимой консолью
            process = subprocess.Popen([
                sys.executable, 
                PROCESSOR_SCRIPT
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
        else:
            # Запуск без видимой консоли
            if os.name == 'nt':  # Windows
                # Используем pythonw.exe для запуска без консоли
                executable = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                if not os.path.exists(executable):
                    executable = sys.executable
                    logger.warning("pythonw.exe не найден, используется обычный python.exe")
                
                process = subprocess.Popen([
                    executable, 
                    PROCESSOR_SCRIPT
                ], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            else:  # Linux/Mac
                process = subprocess.Popen([
                    sys.executable, 
                    PROCESSOR_SCRIPT
                ], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        
        logger.info(f"Процессор уведомлений запущен с PID: {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске процессора уведомлений: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_processor_running():
    """
    Проверяет, запущен ли процессор уведомлений.
    
    Returns:
        bool: True если процессор запущен, False в противном случае.
    """
    try:
        # Для проверки нам нужен psutil
        try:
            import psutil
        except ImportError:
            logger.warning("Модуль psutil не установлен. Установка...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
            logger.info("Модуль psutil успешно установлен")
            import psutil
            
        # Проверяем запущенные процессы
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and len(cmdline) > 1 and PROCESSOR_SCRIPT in cmdline[1]:
                    logger.info(f"Процессор уведомлений работает (PID: {proc.info['pid']})")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        logger.warning("Процессор уведомлений не запущен")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса процессора уведомлений: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def start_and_monitor_processor(check_interval=300, visible=False):
    """
    Запускает процессор уведомлений и периодически проверяет его статус.
    Если процессор остановится, функция автоматически перезапустит его.
    
    Args:
        check_interval (int): Интервал проверки в секундах.
        visible (bool): Если True, процессор будет запущен с видимой консолью.
        
    Returns:
        threading.Thread: Поток мониторинга.
    """
    # Запускаем процессор
    if not start_processor(visible):
        logger.error("Не удалось запустить процессор уведомлений")
    
    # Функция периодической проверки
    def monitor_processor():
        while True:
            time.sleep(check_interval)
            logger.debug("Проверка статуса процессора уведомлений...")
            if not check_processor_running():
                logger.warning("Процессор уведомлений не работает. Попытка перезапуска...")
                if not start_processor(visible):
                    logger.error("Не удалось перезапустить процессор уведомлений")
    
    # Запускаем мониторинг в отдельном потоке
    monitor_thread = threading.Thread(target=monitor_processor, daemon=True)
    monitor_thread.start()
    logger.info(f"Запущен мониторинг процессора уведомлений (интервал проверки: {check_interval} сек)")
    
    return monitor_thread

# Утилита командной строки для запуска процессора
if __name__ == "__main__":
    # Настройка логирования для запуска из командной строки
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)
    
    import argparse
    parser = argparse.ArgumentParser(description='Управление процессором уведомлений')
    parser.add_argument('--visible', action='store_true', help='Запустить процессор с видимой консолью')
    parser.add_argument('--check-only', action='store_true', help='Только проверить статус процессора')
    parser.add_argument('--monitor', action='store_true', help='Запустить процессор и мониторить его статус')
    parser.add_argument('--interval', type=int, default=300, help='Интервал проверки статуса (секунды)')
    
    args = parser.parse_args()
    
    if args.check_only:
        # Только проверка статуса
        is_running = check_processor_running()
        print(f"Процессор уведомлений {'запущен' if is_running else 'не запущен'}")
        sys.exit(0 if is_running else 1)
    elif args.monitor:
        # Запуск с мониторингом
        monitor_thread = start_and_monitor_processor(args.interval, args.visible)
        try:
            # Ждем прерывания с клавиатуры
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Получен сигнал прерывания. Завершение работы...")
            sys.exit(0)
    else:
        # Просто запуск
        is_started = start_processor(args.visible)
        print(f"Процессор уведомлений {'успешно запущен' if is_started else 'не удалось запустить'}")
        sys.exit(0 if is_started else 1) 
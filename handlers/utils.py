"""
Утилитарные функции для обработчиков сообщений.
"""
import os
import sys
import logging
import traceback
import psutil

logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """
    Обработчик ошибок для Telegram бота.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика
    """
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    if update and update.effective_chat:
        await update.effective_chat.send_message(
            "Sorry, an error occurred. Please try again with /start."
        )

def kill_other_bot_instances():
    """
    Останавливает другие экземпляры скрипта бота.
    
    Находит и завершает все процессы Python, которые запускают тот же скрипт,
    что и текущий процесс, кроме самого текущего процесса.
    """
    try:
        current_pid = os.getpid()
        current_script = sys.argv[0]
        
        logger.info(f"Текущий процесс: {current_pid}, скрипт: {current_script}")
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Проверяем, что это процесс Python и запущен тот же скрипт
                if process.pid != current_pid and 'python' in process.name().lower():
                    cmdline = process.cmdline()
                    if len(cmdline) > 1 and current_script in cmdline[-1]:
                        logger.info(f"Останавливаем процесс бота: {process.pid}")
                        process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.warning(f"Ошибка при проверке процесса {process.pid}: {str(e)}")
                pass
        
        logger.info("Проверка других экземпляров завершена")
    except Exception as e:
        logger.error(f"Ошибка в kill_other_bot_instances: {str(e)}", exc_info=True)
        print(f"Error in kill_other_bot_instances: {str(e)}")
        traceback.print_exc() 
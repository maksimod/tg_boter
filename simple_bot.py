from easy_bot import (
    auto_write_translated_message, 
    auto_button, 
    auto_message_with_buttons, 
    start, 
    callback, 
    run_bot, 
    get_user_language
)
from easy_bot import current_update, current_context
from base.survey import survey, create_survey
from chatgpt import chatgpt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import threading
import subprocess
import sys
import logging
from datetime import datetime, timedelta
from notifications import process_notification_request
import os
import time

# Настройка логирования
logger = logging.getLogger('simple_bot')

# Функция для запуска процессора уведомлений в отдельном процессе
def start_notification_processor():
    logger.info("Запуск процессора уведомлений в отдельном процессе")
    try:
        # Проверяем существование файла запуска
        processor_script = 'run_notification_processor.py'
        if not os.path.exists(processor_script):
            logger.error(f"Файл {processor_script} не найден")
            return False
            
        # Проверяем, не запущен ли уже процессор уведомлений
        # Это простая проверка, не гарантирующая точность
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and len(cmdline) > 1 and processor_script in cmdline[1]:
                    logger.info(f"Процессор уведомлений уже запущен (PID: {proc.info['pid']})")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Запускаем отдельный процесс для обработки уведомлений
        process = subprocess.Popen([
            sys.executable, 
            processor_script
        ], 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
        
        logger.info(f"Процессор уведомлений запущен с PID: {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске процессора уведомлений: {e}")
        return False

# Функция для проверки доступности процессора уведомлений
def check_notification_processor():
    try:
        # Проверяем, запущен ли процессор уведомлений
        import psutil
        processor_script = 'run_notification_processor.py'
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and len(cmdline) > 1 and processor_script in cmdline[1]:
                    logger.info(f"Процессор уведомлений работает (PID: {proc.info['pid']})")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        logger.warning("Процессор уведомлений не запущен")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса процессора уведомлений: {e}")
        return False

@start
def start():
    auto_write_translated_message("Привет! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        ["Пройти опрос", "start_survey"],
        ["Спросить ChatGPT", "ask_chatgpt"],
        ["Создать уведомление", "create_notification"],
        [["О боте", "about"], ["Выход", "exit"]]
    ])

@callback("info")
def info():
    auto_write_translated_message("Это информационное сообщение.")
    auto_button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("info_more")
def info_more():
    # Получаем текущий язык пользователя
    lang = get_user_language()
    auto_write_translated_message(f"Я очень простой бот, но я могу работать на разных языках. Сейчас вы используете язык: {lang}")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("help")
def help():
    auto_write_translated_message("Это справочное сообщение. Используйте кнопки для навигации.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("about")
def about():
    auto_write_translated_message("Это простой бот с удобным интерфейсом и поддержкой нескольких языков.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("exit")
def exit():
    auto_write_translated_message("До свидания! Для запуска бота снова используйте /start")

@callback("back_to_menu")
def back():
    start()

@callback("start_survey")
def start_demo_survey():
    # Запускаем тестовый опрос с разными типами данных
    advanced_survey()

@survey("advanced_survey")
def advanced_survey():
    return create_survey([
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Или укажите дату и время вместе (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 15:30 или 'сегодня 15:30')", "дата+время"],
        ["Введите контактный телефон", "телефон"],
        ["Введите ссылку на ваш профиль (начиная с http:// или https://)", "ссылка"],
        ["Вы подтверждаете правильность введенных данных? (да/нет)", "подтверждение"],
        ["Как вы хотели бы продолжить?", [
            [["Вернуться в меню", "back_choice"]],
            [["Информация", "info_choice"], ["Помощь", "help_choice"]]
        ]]
    ], after="action")

@callback("action")
def action_after_survey(answers=None):
    print(f"action_after_survey called with answers: {answers}")
    
    if answers is None:
        # Вызван напрямую как callback, без аргументов
        auto_write_translated_message("Действие после опроса")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])
        return
        
    # Вызван с результатами опроса
    try:
        # Получаем ответы от пользователя
        if len(answers) >= 8:  # Основной опрос
            name = answers[0] if len(answers) > 0 else "не указано"
            age = answers[1] if len(answers) > 1 else "не указан"
            date = answers[2] if len(answers) > 2 else "не указана"
            time = answers[3] if len(answers) > 3 else "не указано"
            datetime_val = answers[4] if len(answers) > 4 else "не указаны"
            phone = answers[5] if len(answers) > 5 else "не указан"
            url = answers[6] if len(answers) > 6 else "не указан"
            confirm = answers[7] if len(answers) > 7 else "не указано"
            choice = answers[8] if len(answers) > 8 else "не сделан"
            
            message = (
                f"Спасибо за заполнение анкеты!\n\n"
                f"ФИО: {name}\n"
                f"Возраст: {age}\n"
                f"Дата встречи: {date}\n"
                f"Время встречи: {time}\n"
                f"Дата и время: {datetime_val}\n"
                f"Телефон: {phone}\n"
                f"Ссылка: {url}\n"
                f"Подтверждение: {confirm}\n"
                f"Выбор: {choice}"
            )
        else:  # Простой опрос с тремя вопросами
            age = answers[0] if len(answers) > 0 else "не указан"
            name = answers[1] if len(answers) > 1 else "не указано"
            mood = answers[2] if len(answers) > 2 else "не указано"
            interaction = answers[3] if len(answers) > 3 else "не указан"
            
            message = f"Спасибо за ответы! Ваш возраст: {age}, имя: {name}, настроение: {mood}, предпочтение: {interaction}"
            
        print(f"Sending survey results: {message}")
        
        if current_update and current_context:
            chat_id = current_update.effective_chat.id
            # Отправляем сообщение напрямую
            asyncio.create_task(current_context.bot.send_message(
                chat_id=chat_id,
                text=message
            ))
            
            # Отправляем кнопку "Вернуться в меню"
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            asyncio.create_task(current_context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            ))
    except Exception as e:
        print(f"Ошибка при обработке результатов опроса: {e}")
        if current_update and current_context:
            chat_id = current_update.effective_chat.id
            asyncio.create_task(current_context.bot.send_message(
                chat_id=chat_id,
                text=f"Произошла ошибка при обработке результатов опроса: {e}"
            ))
    
    # Дополнительная проверка в конце функции
    print("action_after_survey полностью выполнена!")

@survey("my_surv")
def my_surv():
    return create_survey([
        ["Сколько вам лет?", "номер:3-100"],
        ["Как вас зовут?", "текст"],
        ["Как настроение?", "текст"],
        ["Как бы вы хотели со мной взаимодействовать?", [
            [["Информация", "info_choice"], ["Помощь", "help_choice"]],
            ["Пройти опрос", "survey_choice"],
            [["О боте", "about_choice"], ["Выход", "exit_choice"]]
        ]]
    ], after="action")

@callback("ask_chatgpt")
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    
# Обработчик текстовых сообщений для ChatGPT
@chatgpt("Ты - дружелюбный ассистент. Отвечай кратко и по делу на вопросы пользователя.")
def handle_chatgpt_message(message_text):
    # Это функция будет вызвана после обработки запроса ChatGPT
    pass

# Функционал создания уведомлений
@callback("create_notification")
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    notification_survey()

@survey("notification_survey")
def notification_survey():
    return create_survey([
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ], after="process_notification")

@callback("process_notification")
def process_notification(answers=None, update=None, context=None):
    if answers is None:
        auto_write_translated_message("Ошибка при создании уведомления.")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])
        return
    
    try:
        # Получаем ответы из опроса
        notification_datetime = answers[0]
        notification_text = answers[1]
        
        # Получаем ID пользователя для уведомления
        user_id = None
        chat_id = None
        
        # Используем переданные update и context, если они доступны
        current_upd = update or current_update
        current_ctx = context or current_context
        
        if current_upd:
            try:
                user_id = current_upd.effective_user.id
                chat_id = current_upd.effective_chat.id
                print(f"DEBUG: Получен user_id={user_id}, chat_id={chat_id}")
            except Exception as e:
                print(f"DEBUG: Ошибка при получении user_id: {e}")
        
        # Если не удалось получить user_id, используем chat_id
        if not user_id and chat_id:
            print(f"DEBUG: Используем chat_id={chat_id} в качестве user_id")
            user_id = chat_id
            
        # Принудительное получение chat_id, если еще нет
        if not chat_id and current_ctx and current_upd:
            chat_id = current_upd.effective_chat.id
            print(f"DEBUG: Принудительно получен chat_id={chat_id}")
            if not user_id:
                user_id = chat_id
                print(f"DEBUG: Устанавливаем user_id={user_id} равным chat_id")
        
        if not user_id:
            print("DEBUG: Не удалось определить user_id или chat_id")
            auto_write_translated_message("Ошибка: не удалось определить ID пользователя.")
            auto_button([
                ["Вернуться в меню", "back_to_menu"]
            ])
            return
            
        print(f"DEBUG: Создание уведомления для user_id={user_id}, дата={notification_datetime}, текст={notification_text}")
        # Используем функцию из модуля notifications для обработки запроса
        success = process_notification_request(notification_datetime, notification_text, current_upd, current_ctx)
        
        if not success and current_upd and current_ctx:
            # Если произошла ошибка и есть доступ к боту, отправляем сообщение
            chat_id = current_upd.effective_chat.id
            asyncio.create_task(current_ctx.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при создании уведомления. Пожалуйста, проверьте формат даты и времени."
            ))
            
            # Отправляем кнопку возврата в меню
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            asyncio.create_task(current_ctx.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            ))
            
    except Exception as e:
        print(f"Ошибка при обработке уведомления: {e}")
        cur_upd = update or current_update
        cur_ctx = context or current_context
        if cur_upd and cur_ctx:
            chat_id = cur_upd.effective_chat.id
            asyncio.create_task(cur_ctx.bot.send_message(
                chat_id=chat_id,
                text=f"Произошла ошибка при создании уведомления: {e}"
            ))
            
            # Отправляем кнопку возврата в меню
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            asyncio.create_task(cur_ctx.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            ))

# Запуск бота
if __name__ == "__main__":
    try:
        # Проверка наличия модуля psutil
        try:
            import psutil
        except ImportError:
            logger.warning("Модуль psutil не установлен. Установка...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
            logger.info("Модуль psutil успешно установлен")
            import psutil
        
        # Проверяем, нужно ли запускать процессор уведомлений
        # Если переменная окружения установлена, значит процессор уже запущен вручную
        if os.environ.get('NOTIFICATION_PROCESSOR_RUNNING') != '1':
            logger.info("Запуск встроенного процессора уведомлений...")
            # Запускаем процессор уведомлений перед запуском бота
            processor_started = start_notification_processor()
            if not processor_started:
                logger.warning("Не удалось запустить процессор уведомлений. Уведомления могут не отправляться.")
            
            # Периодическая проверка статуса процессора уведомлений
            def check_processor_periodically():
                while True:
                    time.sleep(300)  # Проверка каждые 5 минут
                    if not check_notification_processor():
                        logger.warning("Процессор уведомлений не работает. Попытка перезапуска...")
                        start_notification_processor()
            
            # Запуск периодической проверки в отдельном потоке
            threading.Thread(target=check_processor_periodically, daemon=True).start()
        else:
            logger.info("Процессор уведомлений уже запущен внешним скриптом")
        
        # Запускаем бота
        logger.info("Запуск основного бота...")
        run_bot()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc()) 
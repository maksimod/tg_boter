from easy_bot import (
    auto_write_translated_message, 
    auto_button, 
    auto_message_with_buttons, 
    start, 
    callback, 
    get_user_language,
    get_chat_id_from_update
)
from easy_bot import current_update, current_context
from base.survey import create_survey, survey, start_survey
from chatgpt import chatgpt
import logging
from handlers.survey_handlers import process_survey_results
from notifications.notification_manager import create_notification

logger = logging.getLogger('simple_bot')

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
    # Создаем опрос
    survey_id = "advanced_survey"
    from base.survey import create_survey, start_survey
    import asyncio
    
    # Подготавливаем вопросы для опроса
    questions = [
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
    ]
    
    # Создаем опрос
    create_survey(questions, after="action", survey_id=survey_id)
    
    # Получаем chat_id используя универсальную функцию
    chat_id = get_chat_id_from_update()
    print(f"Получен chat_id: {chat_id}")
    
    if chat_id:
        # Запускаем опрос напрямую
        print(f"Запуск опроса для chat_id: {chat_id}")
        asyncio.create_task(start_survey(survey_id, chat_id, current_context, current_update))
    else:
        print("Ошибка: не удалось определить чат для запуска опроса")
        auto_write_translated_message("Ошибка: не удалось определить чат для запуска опроса.")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])

@callback("action")
def action_after_survey(answers=None, update=None, context=None):
    """
    Обрабатывает результаты опроса
    Вызывается после завершения опроса с результатами
    """
    try:
        from handlers.survey_handlers import process_survey_results
        import asyncio
        from easy_bot import current_update, current_context
        
        # Используем текущие update и context, если они не переданы
        current_upd = update or current_update
        current_ctx = context or current_context
        
        if current_upd and current_ctx:
            # Запускаем асинхронную функцию process_survey_results через create_task
            asyncio.create_task(
                process_survey_results(answers, current_upd, current_ctx)
            )
        else:
            print("Ошибка: Не удалось получить update и context для обработки результатов опроса")
    except Exception as e:
        print(f"Ошибка при обработке результатов опроса: {e}")
        import traceback
        traceback.print_exc()

@callback("ask_chatgpt")
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    
@chatgpt("Ты - дружелюбный ассистент. Отвечай кратко и по делу на вопросы пользователя.")
def handle_chatgpt_message(message_text):
    pass

@callback("create_notification")
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    
    # Создаем опрос
    survey_id = "notification_survey"
    from base.survey import create_survey, start_survey
    import asyncio
    
    # Подготавливаем вопросы для опроса
    questions = [
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ]
    
    # Создаем опрос
    create_survey(questions, after="process_notification", survey_id=survey_id)
    
    # Получаем chat_id используя универсальную функцию
    chat_id = get_chat_id_from_update()
    print(f"[NOTIFICATION] Получен chat_id: {chat_id}")
    
    if chat_id:
        # Запускаем опрос напрямую
        print(f"[NOTIFICATION] Запуск опроса для chat_id: {chat_id}")
        asyncio.create_task(start_survey(survey_id, chat_id, current_context, current_update))
    else:
        print("[NOTIFICATION] Ошибка: не удалось определить чат для запуска опроса")
        auto_write_translated_message("Ошибка: не удалось определить чат для запуска опроса.")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])

@callback("process_notification")
def process_notification(answers=None, update=None, context=None):
    if answers is None:
        auto_write_translated_message("Ошибка при создании уведомления.")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])
        return
    
    current_upd = update or current_update
    current_ctx = context or current_context
    
    if len(answers) >= 2:
        notification_datetime = answers[0]
        notification_text = answers[1]
        create_notification(notification_datetime, notification_text, current_upd, current_ctx)

@callback("multi_survey")
def run_multiple_surveys():
    auto_write_translated_message("Запускаем несколько опросов подряд...")
    
    # Создаем и запускаем несколько опросов один за другим
    import asyncio
    from base.survey import create_survey, start_survey
    
    # Первый опрос - advanced_survey
    survey_id1 = "advanced_survey"
    questions1 = [
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Или укажите дату и время вместе (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 15:30 или 'сегодня 15:30')", "дата+время"],
        ["Введите контактный телефон", "телефон"],
        ["Введите ссылку на ваш профиль (начиная с http:// или https://)", "ссылка"],
        ["Вы подтверждаете правильность введенных данных? (да/нет)", "подтверждение"]
    ]
    create_survey(questions1, after="action", survey_id=survey_id1)
    
    # Второй опрос - my_surv
    survey_id2 = "my_surv"
    questions2 = [
        ["Сколько вам лет?", "номер:3-100"],
        ["Как вас зовут?", "текст"],
        ["Как настроение?", "текст"],
        ["Как бы вы хотели со мной взаимодействовать?", [
            [["Информация", "info_choice"], ["Помощь", "help_choice"]],
            ["Пройти опрос", "survey_choice"],
            [["О боте", "about_choice"], ["Выход", "exit_choice"]]
        ]]
    ]
    create_survey(questions2, after="action", survey_id=survey_id2)
    
    # Получаем chat_id используя универсальную функцию
    chat_id = get_chat_id_from_update()
    print(f"[MULTI_SURVEY] Получен chat_id: {chat_id}")
    
    if chat_id:
        # Запускаем первый опрос
        print(f"[MULTI_SURVEY] Запуск опроса для chat_id: {chat_id}")
        asyncio.create_task(start_survey(survey_id1, chat_id, current_context, current_update))
        auto_write_translated_message("Опросы запущены! Следующий опрос начнется после завершения текущего.")
    else:
        print("[MULTI_SURVEY] Ошибка: не удалось определить чат для запуска опросов")
        auto_write_translated_message("Ошибка: не удалось определить чат для запуска опросов.")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])

if __name__ == "__main__":
    from base.bot_init import initialize_bot
    if not initialize_bot():
        logger.error("Не удалось запустить бота")
        import sys
        sys.exit(1) 
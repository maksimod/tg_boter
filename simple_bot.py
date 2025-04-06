from easy_bot import (
    auto_write_translated_message, 
    auto_button, 
    auto_message_with_buttons, 
    start, 
    callback, 
    get_user_language
)
from easy_bot import current_update, current_context
from base.survey import auto_survey, create_survey, survey
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
    advanced_survey()

@auto_survey("advanced_survey")
def advanced_survey():
    create_survey([
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
    ], after="action", survey_id="advanced_survey")

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

@auto_survey("my_surv")
def my_surv():
    create_survey([
        ["Сколько вам лет?", "номер:3-100"],
        ["Как вас зовут?", "текст"],
        ["Как настроение?", "текст"],
        ["Как бы вы хотели со мной взаимодействовать?", [
            [["Информация", "info_choice"], ["Помощь", "help_choice"]],
            ["Пройти опрос", "survey_choice"],
            [["О боте", "about_choice"], ["Выход", "exit_choice"]]
        ]]
    ], after="action", survey_id="my_surv")

@callback("ask_chatgpt")
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    
@chatgpt("Ты - дружелюбный ассистент. Отвечай кратко и по делу на вопросы пользователя.")
def handle_chatgpt_message(message_text):
    pass

@callback("create_notification")
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    notification_survey()

@auto_survey("notification_survey")
def notification_survey():
    create_survey([
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ], after="process_notification", survey_id="notification_survey")

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
    advanced_survey()
    my_surv()
    auto_write_translated_message("Опросы запущены!")

@survey("main_survey")
def start_main_survey(update, context):
    chat_id = update.message.chat_id
    return create_survey(survey_id="main_survey", title="Основной опрос", questions=advanced_survey.get_questions(), chat_id=chat_id, after_callback=action_after_survey)

if __name__ == "__main__":
    from base.bot_init import initialize_bot
    if not initialize_bot():
        logger.error("Не удалось запустить бота")
        import sys
        sys.exit(1) 
from imports import *
from utils import logger, chat_id, start_custom_survey

@start
def start():
    auto_write_translated_message("Как?")
    auto_write_translated_message("Привет! Я простой бот.")
    auto_write_translated_message("Пока! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        ["Пройти опрос с возможностью редактирования", "start_survey"],
        ["Пройти опрос без возможности редактирования", "start_simple_survey"],
        [["Спросить ChatGPT", "ask_chatgpt"],["Выход", "exit"]],
        ["Создать уведомление", "create_notification"],
        ["Гугл", "google_test"],
        [["О боте", "about"], ["Выход", "exit"]]
    ])

@callback("google_test")
def google_test():
    auto_write_translated_message("Тестим...")
    async def get_google_data(): 
        result = await google_sheets('1XES1siX-OZC6D0vDeElcC1kJ0ZbsEU0j4Tj3n1BzEFM')
        print(result)
    asyncio.create_task(get_google_data())

@callback("info")
def info():
    auto_write_translated_message("Инфа")
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
    survey_id = "advanced_survey"
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
    
    # Добавляем кнопки редактирования для каждого вопроса
    rewrite_data = [
        ["Изменить имя"],
        ["Изменить возраст"],
        ["Изменить дату встречи"],
        ["Изменить время встречи"],
        ["Изменить дату и время встречи"],
        ["Изменить телефон"],
        ["Изменить ссылку на профиль"],
        ["Изменить подтверждение"],
        ["Изменить выбор продолжения"]
    ]
    
    start_custom_survey(questions, "action", survey_id, rewrite_data=rewrite_data)

@callback("action")
def action_after_survey(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    asyncio.create_task(process_survey_results(answers, current_upd, current_ctx))

@callback("ask_chatgpt")
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    
@chatgpt("Отвечай пользователю на английском языке")
def handle_chatgpt_message(message_text):
    pass

@callback("create_notification")
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    
    survey_id = "notification_survey"
    questions = [
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ]
    start_custom_survey(questions, "process_notification", survey_id)

@callback("process_notification")
def process_notification(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    notification_datetime = answers[0]
    notification_text = answers[1]
    create_notification(notification_datetime, notification_text, current_upd, current_ctx)

@callback("start_simple_survey")
def start_simple_survey():
    survey_id = "simple_survey"
    questions = [
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Введите контактный телефон", "телефон"],
        ["Как вы хотели бы продолжить?", [
            [["Вернуться в меню", "back_choice"]],
            [["Информация", "info_choice"]]
        ]]
    ]
    
    # Не передаем rewrite_data, опрос будет работать по стандартной схеме
    start_custom_survey(questions, "action", survey_id)

if __name__ == "__main__":
    from base.bot_init import initialize_bot
    initialize_bot()
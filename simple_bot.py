from easy_bot import (
    auto_write_translated_message, 
    auto_button, 
    auto_message_with_buttons, 
    start, 
    callback, 
    get_user_language
)
from easy_bot import current_update, current_context
from base.survey import survey, create_survey
from chatgpt import chatgpt
import logging
from handlers.survey_handlers import process_survey_results
from notifications.notification_manager import create_notification

# Настройка логирования
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
    # Делегируем обработку результатов опроса в специализированный модуль
    return process_survey_results(answers, current_update, current_context)

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
    
    # Используем переданные update и context, если они доступны
    current_upd = update or current_update
    current_ctx = context or current_context
    
    # Передаем обработку уведомления в специализированный модуль
    if len(answers) >= 2:
        notification_datetime = answers[0]
        notification_text = answers[1]
        create_notification(notification_datetime, notification_text, current_upd, current_ctx)

# Запуск бота
if __name__ == "__main__":
    from base.bot_init import initialize_bot
    # Инициализируем и запускаем бота
    if not initialize_bot():
        logger.error("Не удалось запустить бота")
        import sys
        sys.exit(1) 
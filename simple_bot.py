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
from datetime import datetime, timedelta

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

# Новый функционал для создания уведомлений
@callback("create_notification")
def create_notification():
    auto_write_translated_message("Давайте создадим уведомление.")
    notification_survey()

@survey("notification_survey")
def notification_survey():
    return create_survey([
        ["Введите текст уведомления", "текст"],
        ["Через сколько минут отправить уведомление? (от 1 до 1440)", "номер:1-1440"],
        ["Повторять уведомление? (да/нет)", "подтверждение"]
    ], after="schedule_notification")

@callback("schedule_notification")
def schedule_notification(answers=None):
    if answers is None:
        auto_write_translated_message("Ошибка при создании уведомления.")
        auto_button([
            ["Вернуться в меню", "back_to_menu"]
        ])
        return
    
    try:
        notification_text = answers[0]
        minutes = int(answers[1])
        repeat = answers[2].lower() in ["да", "yes", "true", "1"]
        
        # Получаем текущее время и рассчитываем время отправки
        current_time = datetime.now()
        notification_time = current_time + timedelta(minutes=minutes)
        
        message = (
            f"Уведомление создано!\n\n"
            f"Текст: {notification_text}\n"
            f"Будет отправлено: через {minutes} мин. ({notification_time.strftime('%d.%m.%Y %H:%M')})\n"
            f"Повторение: {'Да' if repeat else 'Нет'}"
        )
        
        if current_update and current_context:
            chat_id = current_update.effective_chat.id
            
            # Регистрируем уведомление (имитация, так как нет настоящего планировщика в этом примере)
            # В реальном приложении здесь был бы код для сохранения уведомления в БД
            # и настройка планировщика задач
            
            # Отправляем подтверждение
            asyncio.create_task(current_context.bot.send_message(
                chat_id=chat_id,
                text=message
            ))
            
            # Симуляция отправки уведомления для демонстрации
            async def send_notification_later():
                await asyncio.sleep(minutes * 60)  # Ждем указанное количество минут
                notification_message = f"🔔 УВЕДОМЛЕНИЕ: {notification_text}"
                await current_context.bot.send_message(chat_id=chat_id, text=notification_message)
                
                if repeat:
                    await current_context.bot.send_message(
                        chat_id=chat_id,
                        text="Это уведомление настроено на повторение."
                    )
            
            # Запускаем асинхронную задачу для отправки уведомления
            asyncio.create_task(send_notification_later())
            
            # Отправляем кнопку возврата в меню
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            asyncio.create_task(current_context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            ))
    except Exception as e:
        print(f"Ошибка при создании уведомления: {e}")
        if current_update and current_context:
            chat_id = current_update.effective_chat.id
            asyncio.create_task(current_context.bot.send_message(
                chat_id=chat_id,
                text=f"Произошла ошибка при создании уведомления: {e}"
            ))

# Запуск бота
if __name__ == "__main__":  run_bot() 
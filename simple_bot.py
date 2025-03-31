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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

@start
def start():
    auto_write_translated_message("Привет! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        ["Пройти опрос", "start_survey"],
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
    my_surv()

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

# Запуск бота
if __name__ == "__main__":  run_bot() 
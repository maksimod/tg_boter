from easy_bot import (
    auto_write_translated_message, 
    auto_button, 
    auto_message_with_buttons, 
    on_auto_start, 
    on_auto_callback, 
    run_bot, 
    get_callback, 
    get_user_language
)

# Токен не нужно указывать здесь, он будет загружен из credentials/telegram/config.py
# или credentials/telegram/token.txt
BOT_TOKEN = None

# Обработчик команды /start
@on_auto_start
def handle_start():
    auto_write_translated_message("Привет! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        [["О боте", "about"], ["Выход", "exit"]]
    ])

# Обработчики callback-кнопок
@on_auto_callback("info")
def handle_info():
    auto_write_translated_message("Это информационное сообщение.")
    auto_button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_auto_callback("info_more")
def handle_info_more():
    # Получаем текущий язык пользователя
    lang = get_user_language()
    auto_write_translated_message(f"Я очень простой бот, но я могу работать на разных языках. Сейчас вы используете язык: {lang}")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_auto_callback("help")
def handle_help():
    auto_write_translated_message("Это справочное сообщение. Используйте кнопки для навигации.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_auto_callback("about")
def handle_about():
    auto_write_translated_message("Это простой бот с удобным интерфейсом и поддержкой нескольких языков.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_auto_callback("exit")
def handle_exit():
    auto_write_translated_message("До свидания! Для запуска бота снова используйте /start")

@on_auto_callback("back_to_menu")
def handle_back():
    handle_start()

# Запуск бота
if __name__ == "__main__":
    run_bot(BOT_TOKEN) 
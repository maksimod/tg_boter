from easy_bot import (
    write_translated_message, 
    button, 
    message_with_buttons, 
    on_start, 
    on_callback, 
    run_bot, 
    get_callback, 
    get_user_language
)

# Токен не нужно указывать здесь, он будет загружен из credentials/telegram/config.py
# или credentials/telegram/token.txt
BOT_TOKEN = None

# Обработчик команды /start
@on_start
async def handle_start():
    await write_translated_message("Привет! Я простой бот.")
    await message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        [["О боте", "about"], ["Выход", "exit"]]
    ])

# Обработчики callback-кнопок
@on_callback("info")
async def handle_info():
    await write_translated_message("Это информационное сообщение.")
    await button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("info_more")
async def handle_info_more():
    # Получаем текущий язык пользователя
    lang = get_user_language()
    await write_translated_message(f"Я очень простой бот, но я могу работать на разных языках. Сейчас вы используете язык: {lang}")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("help")
async def handle_help():
    await write_translated_message("Это справочное сообщение. Используйте кнопки для навигации.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("about")
async def handle_about():
    await write_translated_message("Это простой бот с удобным интерфейсом и поддержкой нескольких языков.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("exit")
async def handle_exit():
    await write_translated_message("До свидания! Для запуска бота снова используйте /start")

@on_callback("back_to_menu")
async def handle_back():
    await handle_start()

# Запуск бота
if __name__ == "__main__":
    run_bot(BOT_TOKEN) 
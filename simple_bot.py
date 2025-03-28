from easy_bot import write_message, button, message_with_buttons, on_start, on_callback, run_bot, get_callback

# Вставьте ваш токен бота здесь
BOT_TOKEN = "7557691355:AAFomvlkd0tU-r3IFn23KQjcv4k3qKwRk3o"

# Обработчик команды /start
@on_start
async def handle_start():
    await write_message("Привет! Я простой бот.")
    await message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        [["О боте", "about"], ["Выход", "exit"]]
    ])

# Обработчики callback-кнопок
@on_callback("info")
async def handle_info():
    await write_message("Это информационное сообщение.")
    await button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("info_more")
async def handle_info_more():
    await write_message("Я очень простой бот, но я могу делать много вещей.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("help")
async def handle_help():
    await write_message("Это справочное сообщение. Используйте кнопки для навигации.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("about")
async def handle_about():
    await write_message("Это простой бот с удобным интерфейсом.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("exit")
async def handle_exit():
    await write_message("До свидания! Для запуска бота снова используйте /start")

@on_callback("back_to_menu")
async def handle_back():
    await handle_start()




# Запуск бота
if __name__ == "__main__":
    run_bot(BOT_TOKEN) 
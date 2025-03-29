from easy_bot import (
    write_translated_message, 
    button, 
    message_with_buttons, 
    on_start, 
    on_callback, 
    on_text_message,
    run_bot
)

# Токен загрузится автоматически из credentials/telegram/token.txt
BOT_TOKEN = None

# Обработчик команды /start
@on_start
async def handle_start():
    await message_with_buttons("Добро пожаловать в бота! Выберите действие:", [
        [["🔍 Поиск информации", "search_info"], ["📅 Создать напоминание", "create_notification"]],
        [["📋 Мои напоминания", "list_notifications"], ["🔔 Проверить напоминания", "check_notifications"]],
        [["ℹ️ О боте", "about"]]
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
    await write_translated_message("Я могу создавать напоминания и работать на разных языках.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("help")
async def handle_help():
    await write_translated_message("Используйте кнопки для навигации и создания напоминаний.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("about")
async def handle_about():
    await write_translated_message("Это бот с напоминаниями и поддержкой нескольких языков.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("exit")
async def handle_exit():
    await write_translated_message("До свидания! Используйте /start для запуска.")

@on_callback("back_to_menu")
async def handle_back():
    await handle_start()

# Обработчики напоминаний
@on_callback("search_info")
async def handle_search_info():
    await write_translated_message("Функция поиска информации в разработке...")
    await button([["Вернуться в главное меню", "back_to_menu"]])

@on_callback("create_notification")
async def handle_create_notification():
    await message_with_buttons("Введите текст напоминания:", [
        [["Отмена", "back_to_menu"]]
    ])

@on_callback("list_notifications")
async def handle_list_notifications():
    # Логика показа напоминаний реализована в easy_bot.py
    pass

@on_callback("check_notifications")
async def handle_check_notifications():
    # Логика проверки напоминаний реализована в easy_bot.py
    pass

@on_text_message
async def handle_text_message(text):
    # Обработка текстовых сообщений для создания напоминаний
    # Логика реализована в easy_bot.py
    pass

# Запуск бота
if __name__ == "__main__":
    run_bot(BOT_TOKEN) 
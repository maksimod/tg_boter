# Easy Telegram Bot

Простой интерфейс для создания Telegram-ботов с поддержкой нескольких языков.

## Установка

1. Установите необходимые зависимости:
```
pip install python-telegram-bot
```

2. Настройте токен бота одним из способов:
   - Создайте файл `credentials/telegram/token.txt` и вставьте туда токен
   - ИЛИ создайте файл `credentials/telegram/config.py` на основе примера `config.py.example`
   - ИЛИ передайте токен напрямую в функцию `run_bot()`

## Быстрый старт

1. Создайте новый файл Python с кодом вашего бота:

```python
from easy_bot import (
    write_translated_message, 
    button, 
    message_with_buttons, 
    on_start, 
    on_callback, 
    run_bot
)

# Обработчик команды /start
@on_start
async def handle_start():
    await write_translated_message("Привет! Я простой бот.")
    await message_with_buttons("Выберите действие:", [
        ["Кнопка 1", "callback_1"],
        ["Кнопка 2", "callback_2"]
    ])

# Обработчик нажатия на кнопку 1
@on_callback("callback_1")
async def handle_button1():
    await write_translated_message("Вы нажали Кнопку 1!")
    await button([
        ["Назад", "back_to_menu"]
    ])

# Обработчик нажатия на кнопку 2
@on_callback("callback_2")
async def handle_button2():
    await write_translated_message("Вы нажали Кнопку 2!")
    await button([
        ["Назад", "back_to_menu"]
    ])

# Обработчик кнопки "Назад"
@on_callback("back_to_menu")
async def handle_back():
    await handle_start()

# Запуск бота
if __name__ == "__main__":
    run_bot()
```

2. Запустите бота:
```
python your_bot_file.py
```

## Доступные функции

- `write_translated_message(text)` - отправляет сообщение пользователю (с переводом на выбранный язык)
- `button([["текст кнопки", "callback_data"]])` - показывает кнопки
- `message_with_buttons("текст", [["кнопка", "callback"]])` - отправляет сообщение с кнопками
- `@on_callback("callback_data")` - декоратор для обработки нажатия кнопки
- `@on_start` - декоратор для обработки команды /start
- `get_callback()` - получает callback_data нажатой кнопки
- `get_user_language()` - получает текущий язык пользователя

## Создание кнопок

Кнопки можно создавать разными способами:

```python
# Одна кнопка в строке
await button([
    ["Кнопка 1", "callback_1"],
    ["Кнопка 2", "callback_2"]
])

# Несколько кнопок в строке
await button([
    [["Кнопка 1", "callback_1"], ["Кнопка 2", "callback_2"]],
    [["Кнопка 3", "callback_3"], ["Кнопка 4", "callback_4"]]
])

# Комбинированный вариант
await button([
    ["Кнопка вверху", "callback_top"],
    [["Левая", "callback_left"], ["Правая", "callback_right"]],
    ["Кнопка внизу", "callback_bottom"]
])
```

## Поддержка языков

Бот автоматически предлагает пользователю выбрать язык при первом запуске. Все сообщения пишутся на русском языке и автоматически переводятся на выбранный пользователем язык.

Поддерживаемые языки:
- Русский (ru)
- Английский (en)
- Украинский (uk)
- Китайский (zh)
- Испанский (es)
- Французский (fr)

## Расширение функциональности

Для добавления новых команд, используйте стандартные обработчики python-telegram-bot: 
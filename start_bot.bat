@echo off
echo Запуск Telegram бота с обработчиком уведомлений...

:: Активация виртуального окружения, если оно есть
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo Виртуальное окружение активировано.
) else (
    echo Виртуальное окружение не найдено. Использую системный Python.
)

:: Запуск бота (запустит и обработчик уведомлений автоматически)
python simple_bot.py

pause 
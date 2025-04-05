@echo off
echo Starting Telegram Bot...

REM Активируем виртуальное окружение, если оно есть
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo No virtual environment found, using system Python
)

REM Проверяем, установлены ли зависимости
python -c "import telegram" 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies! Press any key to exit...
        pause >nul
        exit /b 1
    )
)

REM Запускаем процессор уведомлений в отдельном окне
start "Notification Processor" cmd /c "python run_notification_processor.py > notification_processor.log 2>&1"
echo Notification processor started in separate window

REM Запускаем бота
echo Starting main bot...
python simple_bot.py

REM Если бот остановлен, закрываем все процессы
echo Bot stopped. Press any key to exit...
pause >nul
taskkill /FI "WINDOWTITLE eq Notification Processor" /F
exit /b 0 
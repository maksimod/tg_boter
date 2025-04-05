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

REM Убиваем существующие процессы процессора уведомлений, если они есть
echo Stopping existing notification processors...
taskkill /F /IM pythonw.exe /FI "COMMANDLINE eq *run_notification_processor.py*" 2>NUL
if exist notification_processor_running.txt del notification_processor_running.txt

REM Запускаем процессор уведомлений напрямую с pythonw
echo Starting notification processor in background...
start "" /B pythonw run_notification_processor.py

REM Даем процессору время на инициализацию
echo Waiting for notification processor to initialize...
timeout /t 2 /nobreak >nul

REM Проверяем, что процессор запущен
if exist notification_processor_running.txt (
    echo Notification processor started successfully
) else (
    echo WARNING: Notification processor may not have started correctly
)

REM Запускаем бота
echo Starting main bot...
python simple_bot.py

REM Если бот остановлен, закрываем процесс-обработчик уведомлений
echo Bot stopped. Shutting down notification processor...
taskkill /F /IM pythonw.exe /FI "COMMANDLINE eq *run_notification_processor.py*" 2>NUL
if exist notification_processor_running.txt del notification_processor_running.txt
exit /b 0 
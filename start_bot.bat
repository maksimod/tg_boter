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

REM Создаем временный VBS скрипт для запуска процессора уведомлений без окна
echo Creating invisible launcher...
echo Set WshShell = CreateObject("WScript.Shell") > invisible_launcher.vbs
echo WshShell.Run "cmd.exe /c pythonw.exe run_notification_processor.py > notification_processor.log 2>&1", 0, False >> invisible_launcher.vbs

REM Запускаем процессор уведомлений в фоновом режиме без видимого окна
echo Starting notification processor in background...
wscript.exe //B //Nologo invisible_launcher.vbs

REM Устанавливаем переменную окружения, чтобы simple_bot.py знал, что процессор уже запущен
set NOTIFICATION_PROCESSOR_RUNNING=1

REM Запускаем бота
echo Starting main bot...
python simple_bot.py

REM Если бот остановлен, закрываем процесс-обработчик уведомлений
echo Bot stopped. Shutting down notification processor...
taskkill /F /IM pythonw.exe 2>NUL
REM Удаляем временный VBS скрипт
del /F /Q invisible_launcher.vbs 2>NUL
exit /b 0 
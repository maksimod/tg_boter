@echo off
echo Запуск бота из директории scripts...
cd /d "%~dp0"
call scripts\start_bot.bat
exit /b %errorlevel% 
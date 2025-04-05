@echo off
echo Cleaning up old files...

REM Удаляем перемещенные файлы базы данных
if exist ..\database.py del ..\database.py
if exist ..\check_notification_table.py del ..\check_notification_table.py

REM Удаляем перемещенные файлы уведомлений
if exist ..\run_notification_processor.py del ..\run_notification_processor.py

echo Cleanup completed.
pause 
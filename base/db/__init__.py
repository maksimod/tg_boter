"""
Пакет для работы с базой данных PostgreSQL.
"""
from base.db.database import (
    # Константы
    USERS_TABLE, MESSAGES_TABLE, NOTIFICATIONS_TABLE, MOSCOW_TZ,
    
    # Функции подключения и инициализации
    get_db_connection, init_database, check_database_connection,
    
    # Функции для работы с пользователями
    save_user,
    
    # Функции для работы с сообщениями
    save_message,
    
    # Функции для работы с уведомлениями
    create_notification, get_user_notifications, get_all_active_notifications,
    mark_notification_as_sent, fix_notification_timezone, 
    get_notifications_to_send, get_all_user_notifications, get_db_time
)

__all__ = [
    'USERS_TABLE', 'MESSAGES_TABLE', 'NOTIFICATIONS_TABLE', 'MOSCOW_TZ',
    'get_db_connection', 'init_database', 'check_database_connection',
    'save_user', 'save_message',
    'create_notification', 'get_user_notifications', 'get_all_active_notifications',
    'mark_notification_as_sent', 'fix_notification_timezone', 
    'get_notifications_to_send', 'get_all_user_notifications', 'get_db_time'
] 
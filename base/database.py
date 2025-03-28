"""
Модуль для работы с базой данных PostgreSQL.
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

import asyncpg
from asyncpg import Connection

# Импортируем настройки из модуля конфигурации
try:
    from credentials.postgres.config import (
        HOST, DATABASE, USER, PASSWORD, PORT
    )
    logging.info(f"Загружена конфигурация PostgreSQL.")
except ImportError:
    logging.warning("Не удалось загрузить конфигурацию PostgreSQL, используем значения по умолчанию")
    # Значения по умолчанию
    HOST = "localhost"
    DATABASE = "telegram_bot"
    USER = "postgres"
    PASSWORD = "postgres"
    PORT = 5432

# Глобальная переменная для хранения соединения
_conn: Optional[Connection] = None

async def get_pool():
    """
    Получает соединение с базой данных.
    
    Returns:
        Connection: Соединение с базой данных
    """
    global _conn
    
    if _conn is None or _conn.is_closed():
        try:
            logging.info("Подключаемся к PostgreSQL...")
            print(f"Connecting to PostgreSQL: {HOST}:{PORT}, DB: {DATABASE}")
            
            # Используем точно такой же код, как в check_db.py, который работает
            _conn = await asyncpg.connect(
                host=HOST,
                port=PORT,
                user=USER,
                password=PASSWORD,
                database=DATABASE
            )
            
            logging.info("Соединение с PostgreSQL успешно установлено.")
            
            # Создаем таблицу для переводов, если она не существует
            await init_translation_table()
        except Exception as e:
            logging.error(f"Ошибка при подключении к базе данных: {str(e)}")
            print(f"Database connection error: {str(e)}")
            raise
    
    return _conn

async def close_pool() -> None:
    """
    Закрывает соединение с базой данных.
    """
    global _conn
    
    if _conn is not None and not _conn.is_closed():
        logging.info("Закрываем соединение с PostgreSQL...")
        await _conn.close()
        _conn = None
        logging.info("Соединение с PostgreSQL закрыто.")

async def init_translation_table() -> None:
    """
    Инициализирует таблицу для хранения переводов, если она не существует.
    """
    conn = await get_pool()
    
    try:
        # Проверяем существование таблицы
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'translations')"
        )
        
        if not table_exists:
            # Если таблица не существует, создаём её
            await conn.execute('''
                CREATE TABLE translations (
                    id SERIAL PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language VARCHAR(50) NOT NULL,
                    target_language VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создаем индекс для ускорения поиска
            await conn.execute('''
                CREATE INDEX idx_translations_source_target
                ON translations (source_text, target_language)
            ''')
            
            logging.info("Таблица translations создана успешно.")
        else:
            logging.info("Таблица translations уже существует.")
    except Exception as e:
        logging.error(f"Ошибка при инициализации таблицы translations: {str(e)}")
        print(f"Table initialization error: {str(e)}")
        raise

async def get_translation_from_db(
    source_text: str,
    target_language: str
) -> Optional[str]:
    """
    Получает перевод из базы данных.
    
    Args:
        source_text: Исходный текст
        target_language: Целевой язык
        
    Returns:
        Optional[str]: Переведенный текст или None, если перевод не найден
    """
    conn = await get_pool()
    
    try:
        result = await conn.fetchrow('''
            SELECT translated_text
            FROM translations
            WHERE source_text = $1 AND target_language = $2
            ORDER BY created_at DESC
            LIMIT 1
        ''', source_text, target_language)
        
        if result:
            logging.info(f"Найден кэшированный перевод для '{source_text[:20]}...' на {target_language}")
            return result['translated_text']
        else:
            logging.info(f"Перевод для '{source_text[:20]}...' на {target_language} не найден в БД")
            return None
    except Exception as e:
        logging.error(f"Ошибка при получении перевода из БД: {str(e)}")
        return None

async def save_translation_to_db(
    source_text: str,
    translated_text: str,
    source_language: str,
    target_language: str
) -> bool:
    """
    Сохраняет перевод в базу данных.
    
    Args:
        source_text: Исходный текст
        translated_text: Переведенный текст
        source_language: Исходный язык
        target_language: Целевой язык
        
    Returns:
        bool: True, если перевод успешно сохранен, иначе False
    """
    conn = await get_pool()
    
    try:
        await conn.execute('''
            INSERT INTO translations 
            (source_text, translated_text, source_language, target_language)
            VALUES ($1, $2, $3, $4)
        ''', source_text, translated_text, source_language, target_language)
        
        logging.info(f"Перевод для '{source_text[:20]}...' на {target_language} сохранен в БД")
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении перевода в БД: {str(e)}")
        return False

async def get_translation_statistics() -> List[Dict[str, Any]]:
    """
    Получает статистику переводов из базы данных.
    
    Returns:
        List[Dict[str, Any]]: Список словарей со статистикой переводов
    """
    conn = await get_pool()
    
    try:
        rows = await conn.fetch('''
            SELECT target_language, COUNT(*) as count
            FROM translations
            GROUP BY target_language
            ORDER BY count DESC
        ''')
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Ошибка при получении статистики переводов: {str(e)}")
        return [] 
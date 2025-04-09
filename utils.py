from imports import *
import logging
import asyncio
from typing import List, Union, Optional

logger = logging.getLogger('simple_bot')

def chat_id(update):
    return update.effective_user.id

async def start_custom_survey(questions, callback_name, survey_id, rewrite_data=None):
    from easy_bot import current_context, current_update
    from base.survey import create_survey, start_survey
    
    # Create survey
    survey = create_survey(questions, callback_name, rewrite_data=rewrite_data)
    
    # Start the survey
    asyncio.create_task(start_survey(survey_id, chat_id(current_update), current_context, current_update))
    return True 

async def send_announcement(message_text: str, recipients: Union[List[int], str, int]) -> bool:
    """
    Отправляет объявление указанным получателям через прямое подключение к PostgreSQL.
    
    Args:
        message_text: Текст объявления
        recipients: Получатели (список chat_id, конкретный chat_id или "all" для всех пользователей)
        
    Returns:
        bool: True если отправка успешно выполнена, иначе False
        
    Raises:
        Exception: В случае любой ошибки при работе с PostgreSQL
    """
    from announcement import announce
    
    # Напрямую используем модуль без проверки соединения, так как
    # теперь announce сам напрямую подключается к базе данных
    return await announce(message_text, recipients) 
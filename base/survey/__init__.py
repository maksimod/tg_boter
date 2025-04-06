from .survey import survey, create_survey, get_survey_results, handle_survey_response

# Специальная версия декоратора survey для функций без return
def auto_survey(survey_id):
    """
    Декоратор для функций, которые используют create_survey без return.
    
    Args:
        survey_id: Идентификатор опроса (обязательный)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Оригинальная функция запускается как есть
            func(*args, **kwargs)
            
            # Получаем опрос по его ID
            from .survey import get_last_created_survey
            result = get_last_created_survey(survey_id)
            
            # Для запуска опроса
            from easy_bot import current_update, current_context
            
            if current_update and current_context and current_update.effective_user:
                user_id = current_update.effective_user.id
                chat_id = current_update.effective_chat.id
                
                # Store the active survey for this user
                from .survey import _active_surveys
                _active_surveys[user_id] = {
                    'survey_id': survey_id,
                    'data': result
                }
                
                # Ask the first question directly using the bot
                if result and result.get('questions'):
                    import asyncio
                    from .survey import ask_next_question
                    asyncio.create_task(ask_next_question(
                        current_context, 
                        chat_id, 
                        result
                    ))
            
            return result
        return wrapper
    return decorator

__all__ = ['survey', 'create_survey', 'get_survey_results', 'handle_survey_response', 'auto_survey'] 
from imports import *

logger = logging.getLogger('simple_bot')
chat_id = None

def start_custom_survey(questions, after, survey_id, rewrite_data=None):
    create_survey(questions, after=after, survey_id=survey_id, rewrite_data=rewrite_data)
    chat_id = get_chat_id_from_update()
    asyncio.create_task(start_survey(survey_id, chat_id, current_context, current_update))
    return True 
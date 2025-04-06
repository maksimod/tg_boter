import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

async def process_survey_results(answers, update=None, context=None):
    """
    Обрабатывает результаты опроса и отправляет соответствующее сообщение пользователю.
    
    Args:
        answers: Список ответов на вопросы опроса
        update: Объект Telegram update
        context: Объект Telegram context
    """
    logger.debug(f"Processing survey results: {answers}")
    
    if answers is None or not answers:
        logger.warning("No answers received for survey")
        if update and context:
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text="Действие после опроса"
            )
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            )
    else:
        try:
            chat_id = None
            
            # Получаем chat_id
            if update and hasattr(update, 'effective_chat') and update.effective_chat:
                chat_id = update.effective_chat.id
            elif update and hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat_id
            
            if not chat_id and context and hasattr(context, 'chat_data'):
                # Пробуем получить chat_id из context
                for potential_chat_id in context.chat_data.keys():
                    chat_id = potential_chat_id
                    break
            
            if not chat_id:
                logger.error("Не удалось определить chat_id для отправки результатов опроса")
                return
            
            # Формируем сообщение с ответами
            message = "🔹 <b>Ваши данные:</b>\n\n"
            
            # Получаем вопросы из активного опроса
            questions = []
            if update and update.effective_user:
                user_id = update.effective_user.id
                from base.survey.survey import _active_surveys
                if user_id in _active_surveys:
                    survey_data = _active_surveys[user_id].get('data', {})
                    questions = survey_data.get('questions', [])
            
            # Если удалось получить вопросы, форматируем ответы с их названиями
            if questions and len(questions) >= len(answers):
                for i, answer in enumerate(answers):
                    if i < len(questions):
                        # Извлекаем текст вопроса без пояснений в скобках
                        question_text = questions[i]['text']
                        if '(' in question_text:
                            question_text = question_text.split('(')[0].strip()
                        message += f"🔸 <b>{question_text}:</b> {answer}\n"
                    else:
                        message += f"🔸 <b>Ответ {i+1}:</b> {answer}\n"
            else:
                # Если не удалось получить вопросы, просто выводим ответы
                for i, answer in enumerate(answers):
                    message += f"🔸 <b>Ответ {i+1}:</b> {answer}\n"
            
            logger.debug(f"Sending formatted survey results: {message}")
            
            if context and hasattr(context, 'bot'):
                # Отправляем красивое сообщение напрямую
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML"
                )
                
                # Отправляем кнопку "Вернуться в меню"
                keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Выберите действие:",
                    reply_markup=reply_markup
                )
            else:
                logger.error("Не удалось отправить сообщение: объект context.bot недоступен")
        except Exception as e:
            logger.error(f"Error processing survey results: {e}", exc_info=True)
            if update and context and hasattr(context, 'bot') and chat_id:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Произошла ошибка при обработке результатов опроса: {e}"
                    )
                except Exception as send_error:
                    logger.error(f"Error sending error message: {send_error}", exc_info=True) 
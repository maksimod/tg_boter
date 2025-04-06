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
    
    if answers is None:
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
            # Получаем ответы от пользователя
            if len(answers) >= 8:  # Основной опрос
                name = answers[0] if len(answers) > 0 else "не указано"
                age = answers[1] if len(answers) > 1 else "не указан"
                date = answers[2] if len(answers) > 2 else "не указана"
                time = answers[3] if len(answers) > 3 else "не указано"
                datetime_val = answers[4] if len(answers) > 4 else "не указаны"
                phone = answers[5] if len(answers) > 5 else "не указан"
                url = answers[6] if len(answers) > 6 else "не указан"
                confirm = answers[7] if len(answers) > 7 else "не указано"
                choice = answers[8] if len(answers) > 8 else "не сделан"
                
                message = (
                    f"Спасибо за заполнение анкеты!\n\n"
                    f"ФИО: {name}\n"
                    f"Возраст: {age}\n"
                    f"Дата встречи: {date}\n"
                    f"Время встречи: {time}\n"
                    f"Дата и время: {datetime_val}\n"
                    f"Телефон: {phone}\n"
                    f"Ссылка: {url}\n"
                    f"Подтверждение: {confirm}\n"
                    f"Выбор: {choice}"
                )
            else:  # Простой опрос с тремя вопросами
                age = answers[0] if len(answers) > 0 else "не указан"
                name = answers[1] if len(answers) > 1 else "не указано"
                mood = answers[2] if len(answers) > 2 else "не указано"
                interaction = answers[3] if len(answers) > 3 else "не указан"
                
                message = f"Спасибо за ответы! Ваш возраст: {age}, имя: {name}, настроение: {mood}, предпочтение: {interaction}"
                
            logger.debug(f"Sending survey results: {message}")
            
            if update and context:
                chat_id = update.effective_chat.id
                # Отправляем сообщение напрямую
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
                
                # Отправляем кнопку "Вернуться в меню"
                keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Выберите действие:",
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error processing survey results: {e}", exc_info=True)
            if update and context:
                chat_id = update.effective_chat.id
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Произошла ошибка при обработке результатов опроса: {e}"
                ) 
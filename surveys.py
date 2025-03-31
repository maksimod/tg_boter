"""
Простая система опросов для Telegram бота.
"""
import logging
from typing import Dict, List, Any, Callable, Union
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Константы типов вопросов
TEXT_INPUT = "text"       # Обычный текстовый ввод
NUMBER_INPUT = "number"   # Числовой ввод
BUTTON_CHOICE = "button"  # Выбор из нескольких вариантов

class SurveyManager:
    """
    Менеджер опросов для Telegram бота.
    Управляет созданием, выполнением и обработкой опросов.
    """
    def __init__(self):
        """Инициализация менеджера опросов."""
        self.surveys = {}
        
    def register_survey(self, survey_id: str, questions: List[Dict[str, Any]], 
                      on_complete: Callable):
        """
        Регистрирует новый опрос.
        
        Args:
            survey_id: Уникальный идентификатор опроса
            questions: Список вопросов
            on_complete: Функция, вызываемая при завершении опроса
        """
        self.surveys[survey_id] = {
            'questions': questions,
            'on_complete': on_complete
        }
        logging.info(f"Survey registered: {survey_id} with {len(questions)} questions")
        
    async def start_survey(self, survey_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Начинает опрос для пользователя.
        
        Args:
            survey_id: Идентификатор опроса
            update: Объект обновления Telegram
            context: Контекст бота
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if survey_id not in self.surveys:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Ошибка: Опрос не найден."
            )
            return
        
        survey = self.surveys[survey_id]
        
        # Инициализируем состояние опроса для пользователя
        if 'active_surveys' not in context.user_data:
            context.user_data['active_surveys'] = {}
            
        # Сохраняем состояние активного опроса
        context.user_data['active_surveys'][user_id] = {
            'survey_id': survey_id,
            'current_question': 0,
            'answers': {},
            'chat_id': chat_id
        }
        
        # Задаем первый вопрос
        await self._ask_question(user_id, update, context)
    
    async def _ask_question(self, user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Задает текущий вопрос опроса пользователю.
        
        Args:
            user_id: ID пользователя
            update: Объект обновления Telegram
            context: Контекст бота
        """
        if 'active_surveys' not in context.user_data or user_id not in context.user_data['active_surveys']:
            return
        
        # Получаем данные активного опроса
        survey_data = context.user_data['active_surveys'][user_id]
        survey_id = survey_data['survey_id']
        current_index = survey_data['current_question']
        chat_id = survey_data['chat_id']
        
        # Получаем информацию об опросе
        survey = self.surveys[survey_id]
        questions = survey['questions']
        
        # Проверяем, что еще есть вопросы
        if current_index >= len(questions):
            # Опрос завершен
            await self._complete_survey(user_id, update, context)
            return
        
        # Получаем текущий вопрос
        question = questions[current_index]
        question_type = question['type']
        question_text = question['text']
        
        # Формируем и отправляем вопрос в зависимости от типа
        if question_type == BUTTON_CHOICE:
            # Создаем клавиатуру с вариантами
            options = question['options']
            keyboard = []
            
            # Формируем строки кнопок
            for option_row in options:
                if isinstance(option_row[0], list):
                    # Многострочный вариант
                    row = []
                    for option in option_row:
                        row.append(InlineKeyboardButton(option[0], callback_data=f"survey_{current_index}_{option[1]}"))
                    keyboard.append(row)
                else:
                    # Однострочный вариант
                    keyboard.append([InlineKeyboardButton(option_row[0], callback_data=f"survey_{current_index}_{option_row[1]}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем вопрос с кнопками
            await context.bot.send_message(
                chat_id=chat_id,
                text=question_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            # Обычный текстовый вопрос
            await context.bot.send_message(
                chat_id=chat_id, 
                text=question_text,
                parse_mode="HTML"
            )
    
    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обрабатывает ответ пользователя на вопрос опроса.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст бота
        """
        user_id = update.effective_user.id
        
        # Проверяем, есть ли у пользователя активный опрос
        if 'active_surveys' not in context.user_data or user_id not in context.user_data['active_surveys']:
            return False
        
        survey_data = context.user_data['active_surveys'][user_id]
        survey_id = survey_data['survey_id']
        current_index = survey_data['current_question']
        
        # Получаем опрос и текущий вопрос
        survey = self.surveys[survey_id]
        question = survey['questions'][current_index]
        question_type = question['type']
        
        # Получаем ответ
        answer = None
        
        if question_type == BUTTON_CHOICE:
            # Проверяем, что это callback от кнопки опроса
            if update.callback_query and update.callback_query.data.startswith(f"survey_{current_index}_"):
                # Извлекаем значение из callback_data
                callback_data = update.callback_query.data
                answer = callback_data.split('_', 2)[2]  # Формат: survey_index_value
                
                # Подтверждаем, что callback обработан
                await update.callback_query.answer()
                
                # Для удобства, найдем текст выбранного варианта
                options = question['options']
                display_text = answer  # По умолчанию используем значение
                
                # Поиск текста для отображения
                for option_row in options:
                    if isinstance(option_row[0], list):
                        for option in option_row:
                            if option[1] == answer:
                                display_text = option[0]
                                break
                    elif option_row[1] == answer:
                        display_text = option_row[0]
                        break
                
                # Отображаем ответ пользователю
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Ваш ответ: {display_text}"
                )
            else:
                return False  # Это не ответ на вопрос с кнопками
        elif update.message and update.message.text:
            # Текстовый или числовой ввод
            answer = update.message.text
            
            # Проверка для числового ввода
            if question_type == NUMBER_INPUT:
                try:
                    answer = float(answer)
                except ValueError:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Пожалуйста, введите число."
                    )
                    return True  # Ответ обработан, но неверный формат
        else:
            return False  # Не ответ на вопрос
        
        # Сохраняем ответ
        survey_data['answers'][current_index] = {
            'question': question['text'],
            'answer': answer
        }
        
        # Переходим к следующему вопросу
        survey_data['current_question'] += 1
        
        # Задаем следующий вопрос
        await self._ask_question(user_id, update, context)
        
        return True  # Ответ успешно обработан
    
    async def _complete_survey(self, user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Завершает опрос и вызывает обработчик завершения.
        
        Args:
            user_id: ID пользователя
            update: Объект обновления Telegram
            context: Контекст бота
        """
        if 'active_surveys' not in context.user_data or user_id not in context.user_data['active_surveys']:
            return
        
        # Получаем данные опроса
        survey_data = context.user_data['active_surveys'][user_id]
        survey_id = survey_data['survey_id']
        answers = survey_data['answers']
        
        # Получаем информацию об опросе
        survey = self.surveys[survey_id]
        on_complete = survey['on_complete']
        
        # Преобразуем ответы в формат "вопрос": "ответ"
        formatted_answers = {}
        for idx, answer_data in answers.items():
            formatted_answers[answer_data['question']] = answer_data['answer']
        
        # Вызываем обработчик завершения
        try:
            await on_complete(formatted_answers, update, context)
        except Exception as e:
            logging.error(f"Error in survey completion handler: {str(e)}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при обработке результатов опроса."
            )
        
        # Удаляем опрос из активных
        del context.user_data['active_surveys'][user_id]
    
    async def cancel_survey(self, user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Отменяет текущий опрос пользователя.
        
        Args:
            user_id: ID пользователя
            update: Объект обновления Telegram
            context: Контекст бота
        """
        if 'active_surveys' in context.user_data and user_id in context.user_data['active_surveys']:
            del context.user_data['active_surveys'][user_id]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Опрос отменен."
            )
            return True
        return False


# Создаем глобальный экземпляр менеджера опросов
survey_manager = SurveyManager()


def create_text_question(text):
    """
    Создает вопрос с текстовым вводом.
    
    Args:
        text: Текст вопроса
        
    Returns:
        Dict: Структура вопроса
    """
    return {
        'type': TEXT_INPUT,
        'text': text
    }


def create_number_question(text):
    """
    Создает вопрос с числовым вводом.
    
    Args:
        text: Текст вопроса
        
    Returns:
        Dict: Структура вопроса
    """
    return {
        'type': NUMBER_INPUT,
        'text': text
    }


def create_button_question(text, options):
    """
    Создает вопрос с выбором из вариантов.
    
    Args:
        text: Текст вопроса
        options: Список вариантов ответа
        
    Returns:
        Dict: Структура вопроса
    """
    return {
        'type': BUTTON_CHOICE,
        'text': text,
        'options': options
    }


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик текстовых сообщений для системы опросов.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    
    Returns:
        bool: True, если сообщение было обработано как ответ на вопрос опроса
    """
    return await survey_manager.handle_answer(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback запросов для системы опросов.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    
    Returns:
        bool: True, если callback был обработан как ответ на вопрос опроса
    """
    return await survey_manager.handle_answer(update, context)


async def handle_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /cancel для отмены текущего опроса.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    user_id = update.effective_user.id
    success = await survey_manager.cancel_survey(user_id, update, context)
    if not success:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="У вас нет активных опросов для отмены."
        ) 
from typing import List, Tuple, Dict, Any, Callable, Union, Optional
from functools import wraps
import re
import asyncio
from datetime import datetime, timedelta
import random
import logging

# Global variables to store survey data
_surveys = {}
_active_surveys = {}

# Словарь для хранения последних созданных опросов по ID
_last_created_surveys = {}

# Constants for validation types
TYPE_TEXT = "text"
TYPE_NUMBER = "number"
TYPE_SYMBOLS = "symbols"
TYPE_BUTTONS = "buttons"  # Новый тип для кнопок
TYPE_DATE = "date"        # Тип для даты
TYPE_DATETIME = "datetime"  # Тип для даты со временем
TYPE_TIME = "time"        # Тип для времени
TYPE_PHONE = "phone"      # Тип для телефона
TYPE_URL = "url"          # Тип для ссылки
TYPE_CONFIRM = "confirm"  # Тип для подтверждения
TYPE_NAME = "name"        # Тип для ФИО

# Мультиязычные ключевые слова для дат
DATE_KEYWORDS = {
    "сегодня": {"ru": "сегодня", "en": "today", "uk": "сьогодні", "zh": "今天", "es": "hoy", "fr": "aujourd'hui"},
    "завтра": {"ru": "завтра", "en": "tomorrow", "uk": "завтра", "zh": "明天", "es": "mañana", "fr": "demain"},
    "вчера": {"ru": "вчера", "en": "yesterday", "uk": "вчора", "zh": "昨天", "es": "ayer", "fr": "hier"}
}

# Мультиязычные ключевые слова для подтверждений
CONFIRM_KEYWORDS = {
    "да": {"ru": ["да", "конечно", "точно", "верно"], 
           "en": ["yes", "yeah", "sure", "true"], 
           "uk": ["так", "так-так", "звичайно"], 
           "zh": ["是的", "对", "当然"], 
           "es": ["sí", "claro", "por supuesto"], 
           "fr": ["oui", "bien sûr", "certainement"]},
    "нет": {"ru": ["нет", "неа", "ни за что"], 
            "en": ["no", "nope", "false"], 
            "uk": ["ні", "не"], 
            "zh": ["不", "不是", "否"], 
            "es": ["no", "nunca"], 
            "fr": ["non", "pas"]}
}

class ValidationError(Exception):
    """Exception raised when survey input validation fails."""
    pass

def validate_input(value: str, validation_type: str, validation_params: Optional[dict] = None) -> Any:
    """
    Validates user input based on the specified validation type and parameters.
    
    Args:
        value: The user input to validate
        validation_type: The type of validation to perform
        validation_params: Additional parameters for validation
    
    Returns:
        The validated and possibly converted value
    
    Raises:
        ValidationError: If validation fails
    """
    if validation_type == TYPE_TEXT:
        # Text validation is always valid
        return value
        
    elif validation_type == TYPE_NUMBER:
        try:
            min_val = validation_params.get('min', float('-inf'))
            max_val = validation_params.get('max', float('inf'))
            num_value = float(value)
            
            if num_value < min_val or num_value > max_val:
                raise ValidationError(f"Введите число от {min_val} до {max_val}")
                
            # Return integer if the number is whole
            if num_value.is_integer():
                return int(num_value)
            return num_value
            
        except ValueError:
            raise ValidationError("Пожалуйста, введите корректное число")
            
    elif validation_type == TYPE_SYMBOLS:
        # Only allow specified symbols
        return value
    
    elif validation_type == TYPE_DATE:
        try:
            # Проверяем на ключевые слова
            date_value = _parse_date_keywords(value.lower())
            if date_value:
                return date_value.strftime("%d.%m.%y")
            
            # Проверяем формат даты
            date_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2})$', value)
            if not date_match:
                raise ValidationError("Пожалуйста, введите дату в формате ДД.ММ.ГГ (двузначный год)")
            
            day, month, year = map(int, date_match.groups())
            
            # Проверяем диапазоны значений
            if day < 1 or day > 31:
                raise ValidationError("День должен быть в диапазоне от 1 до 31")
            
            if month < 1 or month > 12:
                raise ValidationError("Месяц должен быть в диапазоне от 1 до 12")
            
            if year < 0 or year > 99:
                raise ValidationError("Год должен быть двузначным числом (от 00 до 99)")
            
            # Корректируем год если задан двузначным числом
            full_year = 2000 + year if year < 50 else 1900 + year
                
            # Проверяем валидность даты (месяцы с разным количеством дней и високосные года)
            days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            
            # Проверка на високосный год для февраля
            if month == 2 and ((full_year % 400 == 0) or (full_year % 100 != 0 and full_year % 4 == 0)):
                days_in_month[2] = 29
                
            # Проверяем, что день не превышает количество дней в месяце
            if day > days_in_month[month]:
                raise ValidationError(f"Некорректная дата: в месяце {month} только {days_in_month[month]} дней")
                
            # Дополнительная проверка через datetime
            try:
                date_value = datetime(full_year, month, day)
                return value  # Возвращаем оригинальное значение, так как оно прошло все проверки
            except ValueError:
                raise ValidationError("Пожалуйста, введите корректную дату")
                
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка в формате даты: {e}")
    
    elif validation_type == TYPE_DATETIME:
        try:
            # Проверяем на ключевые слова
            parts = value.lower().split()
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else "00:00"
            
            # Обрабатываем дату
            date_value = None
            if _is_date_keyword(date_part):
                date_value = _parse_date_keywords(date_part)
            else:
                # Проверяем формат даты
                date_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2})$', date_part)
                if not date_match:
                    raise ValidationError("Пожалуйста, введите дату в формате ДД.ММ.ГГ ЧЧ:ММ (двузначный год)")
                
                day, month, year = map(int, date_match.groups())
                
                # Проверяем диапазоны значений
                if day < 1 or day > 31:
                    raise ValidationError("День должен быть в диапазоне от 1 до 31")
                
                if month < 1 or month > 12:
                    raise ValidationError("Месяц должен быть в диапазоне от 1 до 12")
                
                if year < 0 or year > 99:
                    raise ValidationError("Год должен быть двузначным числом (от 00 до 99)")
                
                # Корректируем год если задан двузначным числом
                full_year = 2000 + year if year < 50 else 1900 + year
                
                # Проверяем валидность даты (месяцы с разным количеством дней и високосные года)
                days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                
                # Проверка на високосный год для февраля
                if month == 2 and ((full_year % 400 == 0) or (full_year % 100 != 0 and full_year % 4 == 0)):
                    days_in_month[2] = 29
                    
                # Проверяем, что день не превышает количество дней в месяце
                if day > days_in_month[month]:
                    raise ValidationError(f"Некорректная дата: в месяце {month} только {days_in_month[month]} дней")
                
                # Проверяем валидность даты
                try:
                    date_value = datetime(full_year, month, day)
                except ValueError:
                    raise ValidationError("Пожалуйста, введите корректную дату")
            
            # Обрабатываем время
            time_match = re.match(r'^(\d{1,2}):(\d{2})$', time_part)
            if not time_match:
                raise ValidationError("Пожалуйста, введите время в формате ЧЧ:ММ")
            
            hour, minute = map(int, time_match.groups())
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValidationError("Пожалуйста, введите корректное время")
            
            # Если дата получена из ключевого слова, добавляем время
            if date_value:
                date_value = date_value.replace(hour=hour, minute=minute)
                return date_value.strftime("%d.%m.%y %H:%M")
            
            # Иначе просто возвращаем введенное значение, которое уже прошло валидацию
            return value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка в формате даты и времени: {e}")
    
    elif validation_type == TYPE_TIME:
        try:
            # Проверяем формат времени
            time_match = re.match(r'^(\d{1,2}):(\d{2})$', value)
            if not time_match:
                raise ValidationError("Пожалуйста, введите время в формате ЧЧ:ММ")
            
            hour, minute = map(int, time_match.groups())
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValidationError("Пожалуйста, введите корректное время")
            
            return value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка в формате времени: {e}")
    
    elif validation_type == TYPE_PHONE:
        try:
            # Удаляем все символы кроме цифр и +
            clean_phone = re.sub(r'[^\d+]', '', value)
            
            # Проверяем что номер состоит из цифр и имеет хотя бы 7 цифр
            if not re.match(r'^\+?\d{7,15}$', clean_phone):
                raise ValidationError("Пожалуйста, введите корректный номер телефона")
            
            return value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка в формате телефона: {e}")
    
    elif validation_type == TYPE_URL:
        try:
            # Проверяем что URL начинается с http:// или https://
            if not re.match(r'^https?://', value):
                raise ValidationError("URL должен начинаться с http:// или https://")
            
            # Проверяем что URL имеет хотя бы один символ после протокола
            if not re.match(r'^https?://[^\s]+$', value):
                raise ValidationError("Пожалуйста, введите корректный URL")
            
            return value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка в формате URL: {e}")
    
    elif validation_type == TYPE_CONFIRM:
        try:
            # Проверяем ключевые слова для подтверждения на разных языках
            value_lower = value.lower()
            
            # Проверяем на положительное подтверждение
            for variants in CONFIRM_KEYWORDS["да"].values():
                if value_lower in variants:
                    return "да"
            
            # Проверяем на отрицательное подтверждение
            for variants in CONFIRM_KEYWORDS["нет"].values():
                if value_lower in variants:
                    return "нет"
            
            raise ValidationError("Пожалуйста, ответьте 'да' или 'нет'")
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка при обработке подтверждения: {e}")
    
    elif validation_type == TYPE_NAME:
        try:
            # Разделяем строку на слова
            words = value.strip().split()
            
            # Проверяем что есть хотя бы два слова
            if len(words) < 2:
                raise ValidationError("Пожалуйста, введите фамилию и имя")
            
            # Проверяем что каждое слово начинается с заглавной буквы для кириллицы
            if any(re.match(r'^[а-яё]', word.lower()) for word in words):  # Если есть кириллические символы
                if any(not re.match(r'^[А-ЯЁ][а-яё]+$', word) for word in words):
                    raise ValidationError("Имя и фамилия должны начинаться с заглавной буквы")
            
            return value
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка при обработке ФИО: {e}")
    
    # Default case
    return value

def _is_date_keyword(text: str) -> bool:
    """Проверяет, является ли текст ключевым словом для даты"""
    text_lower = text.lower()
    for keyword_dict in DATE_KEYWORDS.values():
        if text_lower in keyword_dict.values():
            return True
    return False

def _parse_date_keywords(text: str) -> Optional[datetime]:
    """Преобразует ключевые слова даты в объект datetime"""
    text_lower = text.lower()
    
    # Получаем текущую дату
    today = datetime.now()
    
    # Проверяем ключевое слово "сегодня"
    for lang_value in DATE_KEYWORDS["сегодня"].values():
        if text_lower == lang_value:
            return today
    
    # Проверяем ключевое слово "завтра"
    for lang_value in DATE_KEYWORDS["завтра"].values():
        if text_lower == lang_value:
            return today + timedelta(days=1)
    
    # Проверяем ключевое слово "вчера"
    for lang_value in DATE_KEYWORDS["вчера"].values():
        if text_lower == lang_value:
            return today - timedelta(days=1)
    
    return None

def parse_validation(validation_str: str) -> Tuple[str, Optional[dict]]:
    """
    Parses the validation string to determine type and parameters.
    
    Args:
        validation_str: String specifying validation (e.g. "текст", "номер:3-100")
        or a list of button options
    
    Returns:
        Tuple of (validation_type, params_dict)
    """
    # Если передан список - значит это кнопки
    if isinstance(validation_str, list):
        return TYPE_BUTTONS, {'buttons': validation_str}
    
    # Проверяем различные типы валидации
    if validation_str == "текст":
        return TYPE_TEXT, None
    
    if validation_str == "символы":
        return TYPE_SYMBOLS, None
    
    if validation_str == "дата":
        return TYPE_DATE, None
    
    if validation_str == "дата+время":
        return TYPE_DATETIME, None
    
    if validation_str == "время":
        return TYPE_TIME, None
    
    if validation_str == "телефон":
        return TYPE_PHONE, None
    
    if validation_str == "ссылка":
        return TYPE_URL, None
    
    if validation_str == "подтверждение":
        return TYPE_CONFIRM, None
    
    if validation_str == "фио":
        return TYPE_NAME, None
    
    if validation_str.startswith("номер"):
        # Parse number range
        range_match = re.match(r'номер:(\d+)-(\d+)', validation_str)
        if range_match:
            min_val = int(range_match.group(1))
            max_val = int(range_match.group(2))
            return TYPE_NUMBER, {'min': min_val, 'max': max_val}
    
    # Default to text if no valid format is found
    return TYPE_TEXT, None

def create_survey(questions: List[List], after: Optional[str] = None, survey_id: str = None):
    """
    Creates a survey with the given questions.
    
    Args:
        questions: List of question-validation pairs
        after: Optional callback function name to call after survey completion
        survey_id: Identifier for the survey (required)
    
    Returns:
        Dictionary with survey data
    """
    if survey_id is None:
        survey_id = after
    
    formatted_questions = []
    
    for q in questions:
        question_text = q[0]
        validation_str = q[1]
        
        validation_type, validation_params = parse_validation(validation_str)
        
        formatted_questions.append({
            'text': question_text,
            'validation_type': validation_type,
            'validation_params': validation_params
        })
    
    survey_data = {
        'questions': formatted_questions,
        'current_index': 0,
        'answers': [],
        'after_callback': after
    }
    
    _store_survey(survey_id, survey_data)
    
    return survey_data

def survey(survey_id: str):
    """
    Decorator for creating a survey.
    
    Args:
        survey_id: Unique identifier for the survey
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Call the original function which should return the survey data
            survey_data = func(*args, **kwargs)
            
            # Register the survey
            _surveys[survey_id] = survey_data
            
            # Start the survey for the current user
            from easy_bot import current_update, current_context
            
            if current_update and current_context and current_update.effective_user:
                user_id = current_update.effective_user.id
                chat_id = current_update.effective_chat.id
                
                # Store the active survey for this user
                _active_surveys[user_id] = {
                    'survey_id': survey_id,
                    'data': survey_data
                }
                
                # Ask the first question directly using the bot
                if survey_data['questions']:
                    asyncio.create_task(ask_next_question(
                        current_context, 
                        chat_id, 
                        survey_data
                    ))
                    print(f"Starting survey for chat_id {chat_id}")
            
            return survey_data
        return wrapper
    return decorator

async def handle_survey_response(update, context):
    """
    Handles user response for an active survey.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    
    Returns:
        Boolean indicating if a survey was processed
    """
    if not update.effective_user:
        print("No effective user in update")
        return False
        
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    print(f"Processing response for user {user_id}, chat_id {chat_id}")
    
    # Check if user has an active survey
    if user_id not in _active_surveys:
        print(f"No active survey for user {user_id}")
        return False
    
    active_survey = _active_surveys[user_id]
    survey_data = active_survey['data']
    current_index = survey_data['current_index']
    
    print(f"Current survey index: {current_index}, total questions: {len(survey_data['questions'])}")
    
    # Get the current question
    if current_index >= len(survey_data['questions']):
        # Survey is already completed
        print("Survey already completed")
        return False
    
    question = survey_data['questions'][current_index]
    
    # Проверяем, является ли вопрос кнопочным и есть ли callback данные
    is_button_question = question['validation_type'] == TYPE_BUTTONS
    
    # Если это вопрос с кнопками и пришел callback_query
    if is_button_question and update.callback_query:
        button_value = update.callback_query.data
        # Подтверждаем получение callback запроса
        await update.callback_query.answer()
        
        print(f"Received button choice: {button_value}")
        
        # Сохраняем ответ и переходим к следующему вопросу
        survey_data['answers'].append(button_value)
        survey_data['current_index'] += 1
        current_index = survey_data['current_index']
        
        # Если есть еще вопросы, задаем следующий
        if current_index < len(survey_data['questions']):
            await ask_next_question(context, chat_id, survey_data)
        else:
            # Опрос завершен
            await finish_survey(context, chat_id, user_id, survey_data)
        
        return True
    
    # Обычный текстовый ответ
    if not is_button_question and update.message and update.message.text:
        user_input = update.message.text
        print(f"User input: {user_input}")
        
        try:
            # Validate the input
            validated_value = validate_input(
                user_input, 
                question['validation_type'], 
                question['validation_params']
            )
            
            print(f"Input validated successfully: {validated_value}")
            
            # Store the answer
            survey_data['answers'].append(validated_value)
            
            # Move to the next question
            survey_data['current_index'] += 1
            current_index = survey_data['current_index']
            
            print(f"Moving to question index: {current_index}")
            
            # If there are more questions, ask the next one
            if current_index < len(survey_data['questions']):
                await ask_next_question(context, chat_id, survey_data)
            else:
                # Опрос завершен
                await finish_survey(context, chat_id, user_id, survey_data)
                
        except ValidationError as e:
            # Validation failed, ask again
            print(f"Validation error: {e}")
            # Напрямую отправляем сообщение об ошибке
            await context.bot.send_message(
                chat_id=chat_id,
                text=str(e)
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=question['text']
            )
        except Exception as e:
            print(f"Unexpected error in handle_survey_response: {e}")
            import traceback
            traceback.print_exc()
        
        return True
    
    return False

async def ask_next_question(context, chat_id, survey_data):
    """Задает следующий вопрос опроса"""
    current_index = survey_data['current_index']
    question = survey_data['questions'][current_index]
    
    print(f"Asking next question: {question['text']}")
    
    # Если вопрос требует кнопки
    if question['validation_type'] == TYPE_BUTTONS:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        buttons = question['validation_params'].get('buttons', [])
        keyboard = []
        
        for button_row in buttons:
            if isinstance(button_row, list) and isinstance(button_row[0], list):
                # Это горизонтальный ряд кнопок
                row = []
                for button in button_row:
                    row.append(InlineKeyboardButton(button[0], callback_data=button[1]))
                keyboard.append(row)
            elif isinstance(button_row, list):
                # Это одиночная кнопка
                keyboard.append([InlineKeyboardButton(button_row[0], callback_data=button_row[1])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=question['text'],
            reply_markup=reply_markup
        )
    else:
        # Обычный текстовый вопрос
        await context.bot.send_message(
            chat_id=chat_id,
            text=question['text']
        )

async def finish_survey(context, chat_id, user_id, survey_data):
    """Завершает опрос и вызывает callback функцию"""
    logger = logging.getLogger('survey')
    
    logger.info(f"Survey complete, sending completion message to chat_id {chat_id}")
    print(f"Survey complete, sending completion message to chat_id {chat_id}")
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Спасибо за ваши ответы!"
        )
    except Exception as e:
        logger.error(f"Error sending completion message: {str(e)}")
        print(f"Error sending completion message: {str(e)}")
    
    # Call the after callback if available
    after_callback = survey_data.get('after_callback')
    logger.info(f"Survey complete, calling callback: {after_callback}")
    print(f"Survey complete, calling callback: {after_callback}")
    
    if after_callback:
        try:
            from easy_bot import callbacks, current_update, current_context
            logger.info(f"Imported callbacks module, found callbacks: {list(callbacks.keys())}")
            print(f"Imported callbacks module, found callbacks: {list(callbacks.keys())}")
            
            if after_callback in callbacks:
                callback_func = callbacks[after_callback]
                logger.info(f"Found callback function: {callback_func}")
                print(f"Found callback function: {callback_func}")
                
                try:
                    logger.info(f"Calling callback with answers={len(survey_data['answers'])} items, update={current_update is not None}, context={current_context is not None}")
                    print(f"Calling callback with answers={len(survey_data['answers'])} items, update={current_update is not None}, context={current_context is not None}")
                    
                    # Важно! Используем именованные аргументы вместо позиционных
                    await callback_func(answers=survey_data['answers'], update=current_update, context=current_context)
                    
                    logger.info(f"Callback {after_callback} executed successfully")
                    print(f"Callback {after_callback} executed successfully")
                except Exception as e:
                    logger.error(f"Error in callback {after_callback}: {str(e)}")
                    print(f"Error in callback {after_callback}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    traceback.print_exc()
            else:
                logger.warning(f"Callback {after_callback} not found in registered callbacks")
                print(f"Callback {after_callback} not found in registered callbacks")
        except Exception as e:
            logger.error(f"Error importing callbacks: {str(e)}")
            print(f"Error importing callbacks: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            traceback.print_exc()
    
    # Clear the active survey
    try:
        del _active_surveys[user_id]
        logger.info(f"Cleared active survey for user {user_id}")
        print(f"Cleared active survey for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing active survey: {str(e)}")
        print(f"Error clearing active survey: {str(e)}")

def get_survey_results(survey_id: str) -> List:
    """
    Gets the results of a completed survey.
    
    Args:
        survey_id: ID of the survey
    
    Returns:
        List of answers or empty list if survey not found
    """
    if survey_id in _surveys:
        return _surveys[survey_id].get('answers', [])
    return []

def _run_after_callback(survey_data, answers):
    """
    Internal function to run the after callback with proper error handling
    
    Args:
        survey_data: Survey data
        answers: List of answers from the user
    """
    from easy_bot import callbacks
    
    after_callback = survey_data.get('after_callback')
    if after_callback and after_callback in callbacks:
        try:
            callback_func = callbacks[after_callback]
            callback_func(answers)
        except Exception as e:
            import logging
            logging.error(f"Error running survey callback {after_callback}: {e}") 

def get_last_created_survey(survey_id):
    """
    Возвращает последний созданный опрос с указанным ID
    
    Args:
        survey_id: Идентификатор опроса
        
    Returns:
        dict: Данные опроса или None, если опрос не найден
    """
    return _last_created_surveys.get(survey_id)

def _store_survey(survey_id, survey_data):
    """
    Сохраняет созданный опрос в глобальный словарь
    
    Args:
        survey_id: Идентификатор опроса (обязательный)
        survey_data: Данные опроса
    """
    _last_created_surveys[survey_id] = survey_data
    return survey_data

async def start_survey(survey_id, chat_id, context=None, update=None):
    """
    Запускает опрос непосредственно для указанного пользователя.
    Это функция для прямого запуска опроса без использования декораторов.
    
    Args:
        survey_id: Идентификатор опроса
        chat_id: ID чата, в котором нужно запустить опрос
        context: Объект контекста Telegram (если None, используется current_context)
        update: Объект обновления Telegram (если None, используется current_update)
        
    Returns:
        bool: True, если опрос запущен успешно, False в противном случае
    """
    import logging
    logger = logging.getLogger('survey')
    
    # Используем текущий контекст, если не указан явно
    if context is None:
        from easy_bot import current_context
        context = current_context
    
    # Проверяем наличие контекста
    if context is None:
        logger.error("Не удалось запустить опрос: контекст не определен")
        return False

    # Получаем данные пользователя
    user_id = None
    if update and update.effective_user:
        user_id = update.effective_user.id
    elif context.user_data and hasattr(context, 'user_id'):
        user_id = context.user_id
    else:
        from easy_bot import current_update
        if current_update and current_update.effective_user:
            user_id = current_update.effective_user.id
    
    if user_id is None:
        logger.error("Не удалось запустить опрос: не определен ID пользователя")
        return False
    
    # Получаем данные опроса
    survey_data = get_last_created_survey(survey_id)
    if not survey_data:
        logger.error(f"Не удалось запустить опрос: опрос с ID {survey_id} не найден")
        return False
    
    # Сохраняем опрос как активный для этого пользователя
    _active_surveys[user_id] = {
        'survey_id': survey_id,
        'data': survey_data
    }
    
    # Задаем первый вопрос
    if survey_data.get('questions'):
        import asyncio
        logger.info(f"Запуск опроса {survey_id} для пользователя {user_id} в чате {chat_id}")
        await ask_next_question(context, chat_id, survey_data)
        return True
    else:
        logger.error(f"Не удалось запустить опрос: опрос {survey_id} не содержит вопросов")
        return False 
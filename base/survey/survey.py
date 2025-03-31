from typing import List, Tuple, Dict, Any, Callable, Union, Optional
from functools import wraps
import re
import asyncio

# Global variables to store survey data
_surveys = {}
_active_surveys = {}

# Constants for validation types
TYPE_TEXT = "text"
TYPE_NUMBER = "number"
TYPE_SYMBOLS = "symbols"

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
    
    # Default case
    return value

def parse_validation(validation_str: str) -> Tuple[str, Optional[dict]]:
    """
    Parses the validation string to determine type and parameters.
    
    Args:
        validation_str: String specifying validation (e.g. "текст", "номер:3-100")
    
    Returns:
        Tuple of (validation_type, params_dict)
    """
    if validation_str == "текст":
        return TYPE_TEXT, None
    
    if validation_str == "символы":
        return TYPE_SYMBOLS, None
    
    if validation_str.startswith("номер"):
        # Parse number range
        range_match = re.match(r'номер:(\d+)-(\d+)', validation_str)
        if range_match:
            min_val = int(range_match.group(1))
            max_val = int(range_match.group(2))
            return TYPE_NUMBER, {'min': min_val, 'max': max_val}
    
    # Default to text if no valid format is found
    return TYPE_TEXT, None

def create_survey(questions: List[List], after: Optional[str] = None):
    """
    Creates a survey with the given questions.
    
    Args:
        questions: List of question-validation pairs
        after: Optional callback function name to call after survey completion
    
    Returns:
        Dictionary with survey data
    """
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
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text=survey_data['questions'][0]['text']
                    ))
                    print(f"Sending first question to chat_id {chat_id}")
            
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
    if not update.message or not update.message.text:
        print("No text message in update")
        return False
        
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
            next_question = survey_data['questions'][current_index]['text']
            print(f"Asking next question: {next_question} to chat_id {chat_id}")
            
            # Напрямую отправляем сообщение вместо использования auto_write_translated_message
            await context.bot.send_message(
                chat_id=chat_id,
                text=next_question
            )
        else:
            # Survey is complete
            print(f"Survey complete, sending completion message to chat_id {chat_id}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="Спасибо за ваши ответы!"
            )
            
            # Call the after callback if available
            after_callback = survey_data.get('after_callback')
            print(f"Survey complete, calling callback: {after_callback}")
            
            if after_callback:
                from easy_bot import callbacks
                if after_callback in callbacks:
                    callback_func = callbacks[after_callback]
                    try:
                        callback_func(survey_data['answers'])
                        print(f"Callback {after_callback} executed successfully")
                    except Exception as e:
                        print(f"Error in callback {after_callback}: {e}")
                else:
                    print(f"Callback {after_callback} not found in registered callbacks")
                
            # Clear the active survey
            del _active_surveys[user_id]
            
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
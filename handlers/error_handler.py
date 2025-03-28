import logging
import traceback
from language.language_manager import translate_message

logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Error handler for the bot"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    
    if update and update.effective_chat:
        try:
            # Try to get user's language if available
            lang_code = None
            if context and hasattr(context, 'user_data') and 'language' in context.user_data:
                lang_code = context.user_data['language']
            
            if lang_code:
                # Translate error message to user's language
                translated_error = await translate_message("error_message", lang_code)
                await update.effective_chat.send_message(translated_error)
            else:
                # Fallback to multilingual message
                await update.effective_chat.send_message(
                    "Произошла ошибка / An error occurred / حدث خطأ / एक त्रुटि हुई / ایک خرابی پیش آئی / 发生错误 / Ocurrió un error / Une erreur s'est produite / Сталася помилка. /start"
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}", exc_info=True)
            # Last resort plain message
            await update.effective_chat.send_message(
                "Sorry, an error occurred. Please try again with /start."
            ) 
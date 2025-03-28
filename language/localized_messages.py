from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .language_storage import language_storage
from .translate_any_message import translate_any_message
from base.message import send_message as base_send_message
from base.message import edit_message as base_edit_message

async def send_localized_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
) -> None:
    """
    Отправляет локализованное сообщение пользователю.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        text: Текст сообщения на русском языке
        reply_markup: Разметка клавиатуры
        parse_mode: Режим разбора текста
    """
    user_id = update.effective_chat.id
    target_language = language_storage.get_user_language(user_id)
    
    translated_text = await translate_any_message(text, target_language)
    
    if translated_text is None:
        translated_text = text
    
    await base_send_message(
        update,
        context,
        translated_text,
        reply_markup,
        parse_mode
    )

async def edit_localized_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    message_id: Optional[int] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
) -> None:
    """
    Редактирует сообщение с учетом выбранного языка пользователя.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        text: Текст сообщения на русском языке
        message_id: ID сообщения для редактирования
        reply_markup: Разметка клавиатуры
        parse_mode: Режим разбора текста
    """
    user_id = update.effective_chat.id
    target_language = language_storage.get_user_language(user_id)
    
    translated_text = await translate_any_message(text, target_language)
    
    if translated_text is None:
        translated_text = text
    
    await base_edit_message(
        update,
        context,
        translated_text,
        message_id,
        reply_markup,
        parse_mode
    ) 
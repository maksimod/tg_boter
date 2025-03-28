from typing import Optional, Union, List
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def send_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )

async def edit_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    message_id: Optional[int] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None
) -> None:
    message_id = message_id or update.message.message_id
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=message_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )

async def delete_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: Optional[int] = None
) -> None:
    message_id = message_id or update.message.message_id
    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=message_id
    )

async def send_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    photo: Union[str, bytes],
    caption: Optional[str] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> None:
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=caption,
        reply_markup=reply_markup
    ) 
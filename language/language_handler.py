from typing import Optional
import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from .language_storage import language_storage
from base.keyboard import create_inline_keyboard
from .localized_messages import send_localized_message
from .translate_any_message import translate_any_message

# Определение состояний для выбора языка
CHOOSING_LANGUAGE = 1
SHOWING_MENU = 2  # Добавляем новое состояние

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает меню выбора языка.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        
    Returns:
        int: Следующее состояние диалога
    """
    logging.info("Показываем меню выбора языка")
    
    # Создаем клавиатуру с языками
    keyboard_items = []
    
    # Добавляем кнопки с языками
    for language in language_storage.supported_languages:
        keyboard_items.append({
            'text': language,
            'callback_data': f'language_{language}'
        })
    
    # Создаем клавиатуру с кнопками выбора языка
    keyboard = create_inline_keyboard(keyboard_items, row_width=3)
    
    # Отправляем сообщение с выбором языка
    # Используем базовую функцию send_message, так как перевод еще не настроен
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите язык / Choose language / 选择语言",
        reply_markup=keyboard
    )
    
    return CHOOSING_LANGUAGE

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор языка пользователем.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
        
    Returns:
        int: Следующее состояние диалога
    """
    query = update.callback_query
    if not query:
        logging.error("language_chosen вызван без callback_query")
        return CHOOSING_LANGUAGE
        
    await query.answer()
    
    if query.data and query.data.startswith("language_"):
        chosen_language = query.data.replace("language_", "")
        user_id = update.effective_user.id
        
        logging.info(f"Пользователь {user_id} выбрал язык: {chosen_language}")
        language_storage.set_user_language(user_id, chosen_language)
        
        # Инициализируем предустановленные переводы
        try:
            # Импортируем функцию для инициализации предустановленных переводов
            from easy_bot import init_preset_translations
            await init_preset_translations()
            logging.info("Предустановленные переводы инициализированы")
        except Exception as e:
            logging.error(f"Ошибка при инициализации предустановленных переводов: {e}")
        
        message_text = f"Вы выбрали язык: {chosen_language}. Бот будет отвечать на этом языке."
        
        try:
            logging.info(f"Переводим текст на язык: {chosen_language}")
            translated_text = await translate_any_message(message_text, chosen_language)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=translated_text
            )
            
            logging.info("Переходим к показу главного меню")
            
            if hasattr(context, 'bot_data') and 'main_menu_function' in context.bot_data:
                main_menu_function = context.bot_data['main_menu_function']
                try:
                    context.user_data['chosen_language'] = chosen_language
                    await main_menu_function(update, context)
                    return SHOWING_MENU
                except Exception as e:
                    logging.error(f"Ошибка при вызове главного меню: {str(e)}", exc_info=True)
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Произошла ошибка при показе главного меню. Пожалуйста, отправьте /start для перезапуска бота."
                    )
                    return ConversationHandler.END
            else:
                logging.error("Функция главного меню не найдена в контексте бота")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Ошибка конфигурации бота. Пожалуйста, сообщите администратору."
                )
                return ConversationHandler.END
            
        except Exception as e:
            logging.error(f"Ошибка при обработке выбора языка: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Произошла ошибка при установке языка: {str(e)}"
            )
            return ConversationHandler.END
    
    logging.warning("Получен неверный callback_data при выборе языка")
    return CHOOSING_LANGUAGE 
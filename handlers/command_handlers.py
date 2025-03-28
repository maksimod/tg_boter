import logging
from telegram import Update
from telegram.ext import ConversationHandler

from language.language_manager import (
    translate_message, 
    create_language_keyboard, 
    create_main_menu_keyboard
)

logger = logging.getLogger(__name__)

# Define conversation states
CHOOSING_LANGUAGE, MAIN_MENU, OPTION_SELECTED = range(3)

async def start(update: Update, context) -> int:
    """Start command handler - shows language selection"""
    logger.info("User triggered /start command")
    
    keyboard = create_language_keyboard()
    
    # Multilingual welcome message
    welcome_message = "Выберите язык / Choose language / اختر لغة / भाषा चुनें / زبان منتخب کریں / 选择语言 / Seleccione idioma / Choisissez la langue / Виберіть мову"
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard
    )
    
    return CHOOSING_LANGUAGE

async def language_selected(update: Update, context) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    # Extract language code from callback data
    lang_code = query.data.replace("lang_", "")
    context.user_data["language"] = lang_code
    
    # Get translated message for selected language
    from language.language_manager import LANGUAGES
    language_name = LANGUAGES.get(lang_code, "Unknown")
    language_selected_text = await translate_message("language_selected", lang_code)
    language_selected_text = language_selected_text.format(language=language_name)
    
    await query.edit_message_text(
        text=language_selected_text
    )
    
    # Show main menu
    await show_main_menu(update, context)
    return MAIN_MENU

async def show_main_menu(update: Update, context) -> int:
    """Show main menu for selected language"""
    lang_code = context.user_data.get("language", "en")
    main_menu_text = await translate_message("main_menu", lang_code)
    
    keyboard = await create_main_menu_keyboard(lang_code)
    
    # Different handling based on whether this is a new message or callback
    if update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=main_menu_text,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=main_menu_text,
            reply_markup=keyboard
        )
    
    return MAIN_MENU

async def handle_option(update: Update, context) -> int:
    """Handle menu option selection"""
    query = update.callback_query
    await query.answer()
    
    option = query.data.replace("option_", "")
    lang_code = context.user_data.get("language", "en")
    
    # Get translated message based on selected option
    if option == "info":
        message_key = "info_text"
    elif option == "help":
        message_key = "help_text"
    elif option == "about":
        message_key = "about_text"
    else:
        message_key = None
        message = "Option not recognized"
    
    if message_key:
        message = await translate_message(message_key, lang_code)
    
    await query.edit_message_text(text=message)
    
    # Send the main menu again
    main_menu_text = await translate_message("main_menu", lang_code)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=main_menu_text,
        reply_markup=await create_main_menu_keyboard(lang_code)
    )
    
    return MAIN_MENU 
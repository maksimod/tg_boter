"""
Пакет для обработки многоязычной поддержки телеграм-бота.
"""

from .language_storage import language_storage
from .language_handler import choose_language, language_chosen, CHOOSING_LANGUAGE, SHOWING_MENU
from .localized_messages import send_localized_message, edit_localized_message
from .translate_any_message import translate_any_message 
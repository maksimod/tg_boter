import logging
from typing import Dict, Optional

class LanguageStorage:
    """
    Класс для хранения выбранного языка пользователя.
    В реальном проекте лучше использовать постоянное хранилище 
    (базу данных, Redis и т.д.)
    """
    
    def __init__(self):
        self.user_languages: Dict[int, str] = {}
        # Список поддерживаемых языков
        self.supported_languages = [
            "Русский",
            "Украинский",
            "Английский",
            "Китайский",
            "Испанский",
            "Французский",
            "Урду",
            "Хинди",
            "Арабский"
        ]
        
    def set_user_language(self, user_id: int, language: str) -> None:
        """
        Устанавливает язык для пользователя
        
        Args:
            user_id: ID пользователя
            language: Выбранный язык
        """
        if language not in self.supported_languages:
            logging.warning(f"Попытка установить неподдерживаемый язык: {language}")
            return
            
        self.user_languages[user_id] = language
        logging.info(f"Пользователь {user_id} выбрал язык: {language}")
        
    def get_user_language(self, user_id: int) -> str:
        """
        Получает выбранный пользователем язык
        
        Args:
            user_id: ID пользователя
            
        Returns:
            str: Язык пользователя или "Русский" по умолчанию
        """
        return self.user_languages.get(user_id, "Русский")

# Создаем глобальный экземпляр для использования во всем приложении
language_storage = LanguageStorage() 
from imports import *
from utils import logger, chat_id, start_custom_survey
import sys
import hashlib
sys.path.append('.')  # Add current directory to path
# Import the google_sheets function from our adapter
from google_adapter import google_sheets

# Security switch (can be set to True or False)
INTERNAL_SECURE = True

# Google Sheets IDs
SPREADSHEET_ID = "1g4erzoMJa_22WgvL7WiL_wjeFUIwhlhfj8T7u_6-tOM"
COLLEAGUES_SHEET_ID = "0"
ACCOUNTS_SHEET_ID = "417781023"

# Store authenticated users
authenticated_users = {}

# Function to hash passwords (matching the method used in the sheet)
def hash_password(password):
    # Simple SHA-256 hashing
    return hashlib.sha256(password.encode()).hexdigest()

# Function to check if a user is authenticated
def is_authenticated(user_id=None):
    if user_id is None:
        # Try to get user_id from current_update if not provided
        try:
            if current_update and current_update.effective_user:
                user_id = current_update.effective_user.id
            else:
                return False
        except:
            return False
    
    # Проверяем, что пользователь есть в списке и имеет статус authenticated
    return (user_id in authenticated_users and 
            (isinstance(authenticated_users[user_id], dict) and authenticated_users[user_id].get('authenticated', False) or 
             isinstance(authenticated_users[user_id], bool) and authenticated_users[user_id]))

# Function to start authentication process
@start
def start():
    try:
        user_id = None
        if current_update and hasattr(current_update, 'effective_user') and current_update.effective_user:
            user_id = current_update.effective_user.id
        
        if INTERNAL_SECURE:
            if not is_authenticated(user_id):
                auto_message_with_buttons("Пожалуйста, авторизуйтесь:", [
                    ["Зарегистрироваться", "register"],
                    ["Войти в аккаунт", "login"]
                ])
            else:
                show_main_menu()
        else:
            show_main_menu()
    except Exception as e:
        logger.error(f"Ошибка в функции start: {e}")
        # В случае ошибки показываем меню без проверки авторизации
        show_main_menu()

# Function to show main menu (when authenticated or security is off)
def show_main_menu():
    # Отключаем ChatGPT режим, если был активирован
    try:
        if current_update and hasattr(current_update, 'effective_user') and current_update.effective_user:
            user_id = current_update.effective_user.id
            if user_id in authenticated_users and isinstance(authenticated_users[user_id], dict):
                authenticated_users[user_id]['chatgpt_mode'] = False
    except Exception as e:
        logger.error(f"Ошибка при отключении ChatGPT режима: {e}")
    
    auto_write_translated_message("Привет! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        ["Пройти опрос с возможностью редактирования", "start_survey"],
        ["Пройти опрос без возможности редактирования", "start_simple_survey"],
        [["Спросить ChatGPT", "ask_chatgpt"],["Выход", "exit"]],
        ["Создать уведомление", "create_notification"],
        ["Гугл", "google_test"],
        [["О боте", "about"], ["Выход", "exit"]]
    ])

# Registration handler
@callback("register")
def register():
    try:
        user_id = None
        if current_update and hasattr(current_update, 'effective_user') and current_update.effective_user:
            user_id = current_update.effective_user.id
            # Явно отключаем ChatGPT режим перед началом опроса
            if user_id in authenticated_users and isinstance(authenticated_users[user_id], dict):
                authenticated_users[user_id]['chatgpt_mode'] = False
        
        # Check if already authenticated
        if is_authenticated(user_id):
            auto_write_translated_message("Вы уже авторизованы.")
            show_main_menu()
            return
        
        survey_id = "registration_survey"
        questions = [
            ["Введите Фамилию:", "текст"],
            ["Введите Имя:", "текст"],
            ["Введите Отчество (если есть):", "текст"],
            ["Введите Gmail:", "текст"],
            ["Введите пароль:", "текст"],
            ["Повторите пароль:", "текст"]
        ]
        
        start_custom_survey(questions, "process_registration", survey_id)
    except Exception as e:
        logger.error(f"Ошибка в функции register: {e}")
        auto_write_translated_message("Произошла ошибка при запуске регистрации. Пожалуйста, попробуйте снова.")
        start()

# Registration process handler
@callback("process_registration")
def process_registration(answers=None, update=None, context=None):
    if not answers:
        auto_write_translated_message("Ошибка при регистрации. Пожалуйста, попробуйте снова.")
        return
    
    lastname = answers[0]
    firstname = answers[1]
    middlename = answers[2] if answers[2] else "-"
    gmail = answers[3]
    password = answers[4]
    password_confirm = answers[5]
    
    # Check if passwords match
    if password != password_confirm:
        auto_write_translated_message("Пароли не совпадают. Пожалуйста, попробуйте снова.")
        register()
        return
    
    # Get all colleagues from the sheet
    colleagues = google_sheets('get', SPREADSHEET_ID, COLLEAGUES_SHEET_ID)
    
    # Check if the user exists in colleagues list
    user_found = False
    for colleague in colleagues:
        if (colleague.get('Фамилия', '').lower() == lastname.lower() and 
            colleague.get('Имя', '').lower() == firstname.lower() and 
            (not middlename or middlename == "-" or 
             colleague.get('Отчество', '').lower() == middlename.lower())):
            user_found = True
            break
    
    if not user_found:
        auto_write_translated_message("Пользователь не найден, повторите попытку.")
        register()
        return
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Prepare data for the accounts sheet
    account_data = {
        'фамилия': lastname,
        'имя': firstname,
        'отчество': middlename,
        'почта': gmail,
        'пароль': hashed_password
    }
    
    # Add user to accounts sheet
    result = google_sheets('append', SPREADSHEET_ID, ACCOUNTS_SHEET_ID, account_data)
    
    if result and result.get('success'):
        # Mark user as authenticated
        user_id = None
        try:
            # Get the user ID from the update or current_update
            current_upd = update or current_update
            if current_upd and hasattr(current_upd, 'effective_user') and current_upd.effective_user:
                user_id = current_upd.effective_user.id
                authenticated_users[user_id] = {'authenticated': True, 'chatgpt_mode': False}
                
                auto_write_translated_message("Регистрация успешна! Теперь у вас есть доступ ко всем функциям бота.")
                show_main_menu()
            else:
                auto_write_translated_message("Ошибка при регистрации: не удалось идентифицировать пользователя.")
        except Exception as e:
            logger.error(f"Ошибка при регистрации: {e}")
            auto_write_translated_message("Ошибка при регистрации. Пожалуйста, попробуйте снова.")
    else:
        auto_write_translated_message("Ошибка при регистрации. Пожалуйста, попробуйте снова.")
        register()

# Login handler
@callback("login")
def login():
    try:
        user_id = None
        if current_update and hasattr(current_update, 'effective_user') and current_update.effective_user:
            user_id = current_update.effective_user.id
            # Явно отключаем ChatGPT режим перед началом опроса
            if user_id in authenticated_users and isinstance(authenticated_users[user_id], dict):
                authenticated_users[user_id]['chatgpt_mode'] = False
        
        # Check if already authenticated
        if is_authenticated(user_id):
            auto_write_translated_message("Вы уже авторизованы.")
            show_main_menu()
            return
        
        survey_id = "login_survey"
        questions = [
            ["Введите Gmail:", "текст"],
            ["Введите пароль:", "текст"]
        ]
        
        start_custom_survey(questions, "process_login", survey_id)
    except Exception as e:
        logger.error(f"Ошибка в функции login: {e}")
        auto_write_translated_message("Произошла ошибка при запуске входа. Пожалуйста, попробуйте снова.")
        start()

# Login process handler
@callback("process_login")
def process_login(answers=None, update=None, context=None):
    if not answers:
        auto_write_translated_message("Ошибка при входе. Пожалуйста, попробуйте снова.")
        return
    
    gmail = answers[0]
    password = answers[1]
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Get all accounts from the sheet
    accounts = google_sheets('get', SPREADSHEET_ID, ACCOUNTS_SHEET_ID)
    
    # Check if the account exists with the given credentials
    account_found = False
    for account in accounts:
        if (account.get('почта', '') == gmail and 
            account.get('пароль', '') == hashed_password):
            account_found = True
            break
    
    if account_found:
        # Mark user as authenticated
        try:
            # Get the user ID from the update or current_update
            current_upd = update or current_update
            if current_upd and hasattr(current_upd, 'effective_user') and current_upd.effective_user:
                user_id = current_upd.effective_user.id
                authenticated_users[user_id] = {'authenticated': True, 'chatgpt_mode': False}
                
                auto_write_translated_message("Вход выполнен успешно! Теперь у вас есть доступ ко всем функциям бота.")
                show_main_menu()
            else:
                auto_write_translated_message("Ошибка при входе: не удалось идентифицировать пользователя.")
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            auto_write_translated_message("Ошибка при входе. Пожалуйста, попробуйте снова.")
    else:
        auto_write_translated_message("Аккаунт не найден, повторите попытку.")
        login()

# Middleware to check authentication for protected callbacks
def check_auth(func):
    def wrapper(*args, **kwargs):
        try:
            # First check if update is passed in args or kwargs
            update = kwargs.get('update', None) or (args[0] if len(args) > 0 and hasattr(args[0], 'effective_user') else None)
            
            # If no update in args/kwargs, use current_update
            if update is None:
                update = current_update
            
            # Get user_id safely
            user_id = None
            if update and hasattr(update, 'effective_user') and update.effective_user:
                user_id = update.effective_user.id
                
            if INTERNAL_SECURE and not is_authenticated(user_id):
                auto_write_translated_message("Для доступа к этой функции необходимо авторизоваться.")
                start()
                return
        except Exception as e:
            logger.error(f"Ошибка в check_auth: {e}")
            # Продолжаем выполнение в случае ошибки
            pass
            
        return func(*args, **kwargs)
    return wrapper

# Original callbacks with authentication check
@callback("google_test")
@check_auth
def google_test():
    import json
    import os
    
    auto_write_translated_message("Тестим...")
    # Пример операции 'get' - получение данных из таблицы
    # Первый аргумент: 'get' - тип операции
    # Второй аргумент: ID таблицы
    update_result = google_sheets('delete', '1kRMu66PwqvwluCnL8Wa5TT2YaoXVe2eJ3QzDdF_Yf10', '1297152652', 3, 1)
    print(update_result)
    # Примеры других операций (закомментированы, чтобы не менять данные при тестировании)
    """
    # Пример добавления новой строки
    # Первый аргумент: 'append' - тип операции
    # Второй аргумент: ID таблицы
    # Третий аргумент: ID листа в таблице
    # Четвертый аргумент: словарь с данными для добавления
    append_data = {
        'стоимость': 4000,
        'продолжительность сеанса (мин)': 90,
        'стоимость с акцией': 3500,
        'мин. количество сеансов для акции': 3,
        'доп. информация об акции': 'Специальное предложение'
    }
    append_result = google_sheets('append', '1kRMu66PwqvwluCnL8Wa5TT2YaoXVe2eJ3QzDdF_Yf10', '1297152652', append_data)
    print("Результат добавления:", append_result)
    
    # Пример обновления строки
    # Первый аргумент: 'update' - тип операции
    # Второй аргумент: ID таблицы
    # Третий аргумент: ID листа в таблице
    # Четвертый аргумент: имя поля для идентификации строки
    # Пятый аргумент: словарь с данными для обновления
    update_data = {
        'стоимость': 4000,
        'стоимость с акцией': 3500,
        'доп. информация об акции': 'Обновленное описание акции'
    }
    update_result = google_sheets('update', '1kRMu66PwqvwluCnL8Wa5TT2YaoXVe2eJ3QzDdF_Yf10', '1297152652', 'стоимость', update_data)
    print("Результат обновления:", update_result)
    
    # Пример удаления строки
    # Первый аргумент: 'delete' - тип операции
    # Второй аргумент: ID таблицы
    # Третий аргумент: ID листа в таблице
    # Четвертый аргумент: номер начальной строки для удаления
    # Пятый аргумент: количество строк для удаления
    delete_result = google_sheets('delete', '1kRMu66PwqvwluCnL8Wa5TT2YaoXVe2eJ3QzDdF_Yf10', '1297152652', 3, 1)
    print("Результат удаления:", delete_result)
    """

@callback("info")
@check_auth
def info():
    auto_write_translated_message("Инфа")
    auto_button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("info_more")
@check_auth
def info_more():
    lang = get_user_language()
    auto_write_translated_message(f"Я очень простой бот, но я могу работать на разных языках. Сейчас вы используете язык: {lang}")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("help")
@check_auth
def help():
    auto_write_translated_message("Это справочное сообщение. Используйте кнопки для навигации.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("about")
@check_auth
def about():
    auto_write_translated_message("Это простой бот с удобным интерфейсом и поддержкой нескольких языков.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("exit")
@check_auth
def exit():
    auto_write_translated_message("До свидания! Для запуска бота снова используйте /start")

@callback("back_to_menu")
@check_auth
def back():
    start()

@callback("start_survey")
@check_auth
def start_demo_survey():
    survey_id = "advanced_survey"
    questions = [
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Или укажите дату и время вместе (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 15:30 или 'сегодня 15:30')", "дата+время"],
        ["Введите контактный телефон", "телефон"],
        ["Введите ссылку на ваш профиль (начиная с http:// или https://)", "ссылка"],
        ["Вы подтверждаете правильность введенных данных? (да/нет)", "подтверждение"],
        ["Как вы хотели бы продолжить?", [
            [["Вернуться в меню", "back_choice"]],
            [["Информация", "info_choice"], ["Помощь", "help_choice"]]
        ]]
    ]
    
    # Добавляем кнопки редактирования для каждого вопроса
    rewrite_data = [
        ["Изменить имя"],
        ["Изменить возраст"],
        ["Изменить дату встречи"],
        ["Изменить время встречи"],
        ["Изменить дату и время встречи"],
        ["Изменить телефон"],
        ["Изменить ссылку на профиль"],
        ["Изменить подтверждение"],
        ["Изменить выбор продолжения"]
    ]
    
    start_custom_survey(questions, "action", survey_id, rewrite_data=rewrite_data)

@callback("action")
@check_auth
def action_after_survey(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    asyncio.create_task(process_survey_results(answers, current_upd, current_ctx))

@callback("ask_chatgpt")
@check_auth
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    # Устанавливаем флаг, что пользователь хочет использовать ChatGPT
    user_id = current_update.effective_user.id
    authenticated_users[user_id] = {'authenticated': True, 'chatgpt_mode': True}
    
@chatgpt("Отвечай пользователю на английском языке")
def handle_chatgpt_message(message_text):
    # Проверяем, авторизован ли пользователь и активировал ли ChatGPT режим
    try:
        user_id = current_update.effective_user.id
        if not INTERNAL_SECURE or (user_id in authenticated_users and 
                                   authenticated_users[user_id].get('authenticated') and 
                                   authenticated_users[user_id].get('chatgpt_mode')):
            # Обрабатываем запрос только если пользователь авторизован и активировал ChatGPT
            pass  # Реальная обработка происходит внутри декоратора @chatgpt
        else:
            # Не обрабатываем сообщение, если пользователь не авторизован или не активировал ChatGPT
            return False
    except Exception as e:
        logger.error(f"Ошибка в обработке ChatGPT сообщения: {e}")
        return False

@callback("create_notification")
@check_auth
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    
    survey_id = "notification_survey"
    questions = [
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ]
    start_custom_survey(questions, "process_notification", survey_id)

@callback("process_notification")
@check_auth
def process_notification(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    notification_datetime = answers[0]
    notification_text = answers[1]
    create_notification(notification_datetime, notification_text, current_upd, current_ctx)

@callback("start_simple_survey")
@check_auth
def start_simple_survey():
    survey_id = "simple_survey"
    questions = [
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Введите контактный телефон", "телефон"],
        ["Как вы хотели бы продолжить?", [
            [["Вернуться в меню", "back_choice"]],
            [["Информация", "info_choice"]]
        ]]
    ]
    
    # Не передаем rewrite_data, опрос будет работать по стандартной схеме
    start_custom_survey(questions, "action", survey_id)

if __name__ == "__main__":
    from base.bot_init import initialize_bot
    initialize_bot()
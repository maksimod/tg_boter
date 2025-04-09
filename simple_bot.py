from imports import *
from utils import logger, chat_id, start_custom_survey

@start
def start():
    auto_write_translated_message("Как?")
    auto_write_translated_message("Привет! Я простой бот.")
    auto_write_translated_message("Пока! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        ["Пройти опрос с возможностью редактирования", "start_survey"],
        ["Пройти опрос без возможности редактирования", "start_simple_survey"],
        [["Спросить ChatGPT", "ask_chatgpt"],["Выход", "exit"]],
        ["Создать уведомление", "create_notification"],
        ["Гугл", "google_test"],
        [["О боте", "about"], ["Выход", "exit"]],
        ["Создать объявление", "create_announcement"],
        ["Тестовое объявление", "test_announcement"]
    ])

@callback("google_test")
def google_test():
    auto_write_translated_message("Тестим...")
    async def get_google_data(): 
        result = await google_sheets('1XES1siX-OZC6D0vDeElcC1kJ0ZbsEU0j4Tj3n1BzEFM')
        print(result)
    asyncio.create_task(get_google_data())

@callback("info")
def info():
    auto_write_translated_message("Инфа")
    auto_button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("info_more")
def info_more():
    lang = get_user_language()
    auto_write_translated_message(f"Я очень простой бот, но я могу работать на разных языках. Сейчас вы используете язык: {lang}")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("help")
def help():
    auto_write_translated_message("Это справочное сообщение. Используйте кнопки для навигации.")
    
    async def announce_example():
        try:
            # Получаем chat_id текущего пользователя
            current_chat_id = get_chat_id_from_update()
            logger.info(f"ID чата текущего пользователя для объявления: {current_chat_id}")
            
            if current_chat_id:
                success = await announce("ВНИМАНИЕ ВСЕМ", [current_chat_id])
                if success:
                    logger.info(f"Тестовое объявление отправлено пользователю {current_chat_id}")
                else:
                    logger.error("Не удалось отправить тестовое объявление")
            else:
                logger.error("Не удалось получить ID чата текущего пользователя")
        except Exception as e:
            logger.error(f"Ошибка при отправке тестового объявления: {e}")
    
    # Запускаем асинхронную задачу для отправки объявления
    asyncio.create_task(announce_example())
    
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("about")
def about():
    auto_write_translated_message("Это простой бот с удобным интерфейсом и поддержкой нескольких языков.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("exit")
def exit():
    auto_write_translated_message("До свидания! Для запуска бота снова используйте /start")

@callback("back_to_menu")
def back():
    start()

@callback("start_survey")
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
def action_after_survey(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    asyncio.create_task(process_survey_results(answers, current_upd, current_ctx))

@callback("ask_chatgpt")
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    
@chatgpt("Отвечай пользователю на английском языке")
def handle_chatgpt_message(message_text):
    pass

@callback("create_notification")
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    
    survey_id = "notification_survey"
    questions = [
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ]
    start_custom_survey(questions, "process_notification", survey_id)

@callback("process_notification")
def process_notification(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    notification_datetime = answers[0]
    notification_text = answers[1]
    create_notification(notification_datetime, notification_text, current_upd, current_ctx)

@callback("start_simple_survey")
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

@callback("create_announcement")
def create_announcement_callback():
    auto_write_translated_message("Давайте создадим объявление.")
    
    survey_id = "announcement_survey"
    questions = [
        ["Введите текст объявления", "текст"],
        ["Выберите получателей:", [
            [["Все пользователи", "all_recipients"]],
            [["Указать конкретных пользователей", "specific_recipients"]]
        ]]
    ]
    start_custom_survey(questions, "process_announcement", survey_id)

@callback("process_announcement")
def process_announcement(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    announcement_text = answers[0]
    recipient_choice = answers[1]
    
    current_chat_id = get_chat_id_from_update(current_upd)
    logger.info(f"ID чата текущего пользователя: {current_chat_id}")
    
    if recipient_choice == "all_recipients":
        # Отправляем всем пользователям
        auto_write_translated_message("Отправляю объявление всем пользователям...")
        
        async def send_to_all():
            try:
                # Отправляем объявление всем пользователям
                success = await announce(announcement_text, "all")
                
                if success:
                    auto_write_translated_message("Объявление успешно отправлено всем пользователям.")
                else:
                    # Если отправка не удалась, пробуем отправить только текущему пользователю
                    logger.warning("Не удалось отправить всем пользователям, пробуем отправить только вам.")
                    if current_chat_id:
                        direct_success = await announce(announcement_text, [current_chat_id])
                        if direct_success:
                            auto_write_translated_message("Объявление отправлено только вам из-за проблем с базой данных.")
                        else:
                            auto_write_translated_message("Не удалось отправить объявление. Пожалуйста, попробуйте позже.")
                    else:
                        auto_write_translated_message("Не удалось отправить объявление. Пожалуйста, попробуйте позже.")
            except Exception as e:
                logger.error(f"Ошибка при отправке объявления: {str(e)}")
                auto_write_translated_message(f"Произошла ошибка: {str(e)}")
                
                # В любом случае пробуем отправить текущему пользователю
                if current_chat_id:
                    try:
                        await announce(announcement_text, [current_chat_id])
                        auto_write_translated_message("Объявление отправлено только вам.")
                    except Exception:
                        pass
        
        asyncio.create_task(send_to_all())
    elif recipient_choice == "specific_recipients":
        # Запрашиваем конкретные ID пользователей
        auto_write_translated_message("Введите ID пользователей через запятую (например: 123456789, 987654321)")
        
        # Настраиваем обработчик сообщений для получения списка ID
        @on_auto_text_message
        async def handle_user_ids(message_text):
            try:
                if message_text.strip().lower() == "я":
                    # Если пользователь вводит "я", отправляем только ему
                    user_ids = [current_chat_id]
                    auto_write_translated_message(f"Отправляю объявление только вам (ID: {current_chat_id})...")
                else:
                    # Парсим список ID через запятую
                    user_ids = [int(user_id.strip()) for user_id in message_text.split(',')]
                    
                    # Проверяем, включен ли текущий пользователь
                    if current_chat_id and current_chat_id not in user_ids:
                        user_ids.append(current_chat_id)
                        auto_write_translated_message(f"Добавлен ваш ID ({current_chat_id}) к списку получателей.")
                
                # Отправляем объявление
                auto_write_translated_message("Отправляю объявление...")
                success = await announce(announcement_text, user_ids)
                
                if success:
                    auto_write_translated_message(f"Объявление отправлено {len(user_ids)} пользователям.")
                else:
                    auto_write_translated_message("Не удалось отправить объявление. Пожалуйста, попробуйте позже.")
            except ValueError:
                auto_write_translated_message("Неверный формат ID. Используйте только числа, разделённые запятыми, или введите 'я' для отправки только себе.")
            except Exception as e:
                logger.error(f"Ошибка при обработке ID пользователей: {e}")
                auto_write_translated_message(f"Произошла ошибка: {str(e)}")
    
    # Возвращаемся в главное меню
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("test_announcement")
def test_announcement():
    auto_write_translated_message("Отправляю тестовое объявление...")
    
    # Получаем ID чата текущего пользователя
    current_chat_id = get_chat_id_from_update()
    logger.info(f"ID чата текущего пользователя для тестового объявления: {current_chat_id}")
    
    async def send_test_directly():
        try:
            if current_chat_id:
                message = "Это тестовое сообщение для проверки функциональности объявлений."
                
                # Получаем экземпляр бота напрямую для отправки сообщения
                from easy_bot import get_bot_instance
                app = get_bot_instance()
                
                if app and hasattr(app, 'bot'):
                    logger.info(f"Отправка тестового сообщения напрямую через bot.send_message")
                    await app.bot.send_message(chat_id=current_chat_id, text=message)
                    auto_write_translated_message("Тестовое сообщение отправлено напрямую! Проверьте что оно пришло.")
                else:
                    logger.error("Не удалось получить экземпляр бота для отправки")
                    auto_write_translated_message("Не удалось получить экземпляр бота для отправки. Проверьте логи.")
            else:
                auto_write_translated_message("Не удалось определить ваш ID чата.")
        except Exception as e:
            logger.error(f"Ошибка при прямой отправке тестового сообщения: {e}")
            auto_write_translated_message(f"Ошибка при отправке: {str(e)}")
    
    asyncio.create_task(send_test_directly())
    
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

if __name__ == "__main__":
    from base.bot_init import initialize_bot
    initialize_bot()
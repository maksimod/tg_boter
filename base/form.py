from typing import Dict, List, Optional, Callable, Any
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

class Form:
    """A class to handle sequential form questions."""
    
    def __init__(
        self,
        questions: List[Dict[str, Any]],
        on_complete: Callable[[Dict[str, Any], Update, ContextTypes.DEFAULT_TYPE], Any]
    ):
        """
        Initialize a form with questions and completion callback.
        
        Args:
            questions: List of question dictionaries with keys:
                - text: Question text
                - field: Field name to store answer
                - validation: Optional validation function
                - keyboard: Optional keyboard for the question
            on_complete: Callback function called when form is complete
        """
        self.questions = questions
        self.on_complete = on_complete
        self.current_question = 0
        self.answers: Dict[str, Any] = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the form by asking the first question."""
        await self._ask_question(update, context)
        return self.current_question
    
    async def handle_answer(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle the user's answer to the current question."""
        question = self.questions[self.current_question]
        answer = update.message.text if update.message else update.callback_query.data
        
        # Validate answer if validation function exists
        if 'validation' in question:
            try:
                answer = question['validation'](answer)
            except ValueError as e:
                chat_id = update.effective_chat.id
                await context.bot.send_message(chat_id=chat_id, text=str(e))
                return self.current_question
        
        # Store answer
        self.answers[question['field']] = answer
        
        # Move to next question or complete
        self.current_question += 1
        if self.current_question < len(self.questions):
            await self._ask_question(update, context)
            return self.current_question
        else:
            await self.on_complete(self.answers, update, context)
            return ConversationHandler.END
    
    async def _ask_question(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Ask the current question to the user."""
        question = self.questions[self.current_question]
        keyboard = question.get('keyboard')
        chat_id = update.effective_chat.id
        
        if keyboard:
            await context.bot.send_message(
                chat_id=chat_id,
                text=question['text'],
                reply_markup=keyboard
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=question['text']
            )
    
    def get_answers(self) -> Dict[str, Any]:
        """Get all collected answers."""
        return self.answers.copy()

# Example usage:
"""
def validate_email(email: str) -> str:
    if '@' not in email:
        raise ValueError("Please enter a valid email address")
    return email

async def on_form_complete(answers: Dict[str, Any], update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Thank you! Your answers: {answers}")

questions = [
    {
        'text': 'What is your name?',
        'field': 'name'
    },
    {
        'text': 'What is your email?',
        'field': 'email',
        'validation': validate_email
    },
    {
        'text': 'Choose your preferred language:',
        'field': 'language',
        'keyboard': create_inline_keyboard([
            {'text': 'English', 'callback_data': 'en'},
            {'text': 'Russian', 'callback_data': 'ru'}
        ])
    }
]

form = Form(questions, on_form_complete)
""" 
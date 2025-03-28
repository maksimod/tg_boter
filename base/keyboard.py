from typing import List, Dict, Union
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_inline_keyboard(
    buttons: List[Dict[str, str]],
    row_width: int = 2
) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    
    for button in buttons:
        row.append(InlineKeyboardButton(
            text=button['text'],
            callback_data=button['callback_data']
        ))
        
        if len(row) == row_width:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def create_url_keyboard(
    buttons: List[Dict[str, str]],
    row_width: int = 2
) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    
    for button in buttons:
        row.append(InlineKeyboardButton(
            text=button['text'],
            url=button['url']
        ))
        
        if len(row) == row_width:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def create_mixed_keyboard(
    buttons: List[Dict[str, Union[str, bool]]],
    row_width: int = 2
) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    
    for button in buttons:
        if 'callback_data' in button:
            btn = InlineKeyboardButton(
                text=button['text'],
                callback_data=button['callback_data']
            )
        else:
            btn = InlineKeyboardButton(
                text=button['text'],
                url=button['url']
            )
        
        row.append(btn)
        
        if len(row) == row_width:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard) 
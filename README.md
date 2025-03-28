# Multilingual Telegram Bot

A scalable Telegram bot with multilingual support, Google service integration (Sheets/Drive), and form processing capabilities.

## Features

- Multi-language support with automatic translation
- Form processing system
- Google Sheets integration
- Google Drive integration
- Modular architecture for extensibility

## Project Structure

```
├── base/                  # Core functionality
│   ├── form.py            # Form processing
│   ├── keyboard.py        # Keyboard creation utilities
│   └── message.py         # Message handling utilities
├── credentials/           # API credentials
│   ├── google/            # Google API credentials
│   ├── openai/            # OpenAI API credentials
│   └── telegram/          # Telegram bot credentials
├── google/                # Google API integrations
│   ├── drive.py           # Google Drive integration
│   └── sheets.py          # Google Sheets integration
├── language/              # Language support
│   ├── language_handler.py     # Language selection handlers
│   ├── language_storage.py     # User language preferences
│   ├── localized_messages.py   # Message localization
│   └── translate_any_message.py # Translation service
├── main.py                # Main bot application
└── requirements.txt       # Project dependencies
```

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Configure credentials:
   - Create a `config.py` file in `credentials/telegram/` with your bot token and settings
   - Set up Google API credentials in `credentials/google/`
   - Set up OpenAI API key in `credentials/openai/` or as environment variable

## Usage

Run the bot:
```
python main.py
```

## Adding New Features

The modular architecture makes it easy to extend the bot:

1. Add new handlers in `main.py`
2. Create new utility modules in `base/` for reusable functionality
3. Add new language support in `language/language_storage.py`

## License

MIT 
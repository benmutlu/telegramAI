# lead-qualifier

Structured lead intake for Telegram private chats.

`lead-qualifier` is a Telegram addon for collecting consistent lead information in private chat. Instead of letting every conversation start with unstructured messages, it walks the user through a short intake flow and stores the responses in SQLite.

## What it does

When a user starts the flow:

1. The bot asks for the user's name.
2. The bot asks for the company name.
3. The bot asks for a contact email.
4. The bot asks what the user needs help with.
5. The bot stores the result in SQLite.

This gives you a simple first-pass qualification layer before a sales or support team follows up.

## Features

- multi-step intake flow
- SQLite-backed lead storage
- restart and reset support
- simple status lookup
- self-hostable setup

## Commands

- `/start`: start or restart the intake flow
- `/status`: show whether the current user has completed a lead submission
- `/reset`: clear the current flow state and start over

## Setup

```bash
cd addons/lead-qualifier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Configuration

- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather
- `DB_PATH`: SQLite database path
- `INTRO_MESSAGE`: first message shown to the user
- `SUCCESS_MESSAGE`: message shown after lead capture
- `LOG_LEVEL`: logging level

## Intended use

This addon works well for:

- inbound sales qualification
- simple support intake
- collecting structured data before handoff
- replacing repetitive first-response questions

## Limitations

- private chat only in the current version
- no admin dashboard yet
- no external CRM sync yet


# captcha-guard

Image captcha verification for private Telegram bot chats.

## Features

- 6-character image captcha
- Noise and line obfuscation
- SQLite-backed user state
- Retry counting and temporary lockouts
- Short command set for simple onboarding

## Commands

- `/start`: start verification
- `/captcha`: send a fresh captcha
- `/status`: show current verification state
- `/resetcaptcha`: clear state and restart verification

## Setup

```bash
cd addons/captcha-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Configuration

- `TELEGRAM_BOT_TOKEN`: bot token from BotFather
- `CAPTCHA_TTL_SECONDS`: how long a captcha stays valid
- `MAX_ATTEMPTS`: wrong answers before lockout
- `LOCKOUT_SECONDS`: lockout duration after too many failures
- `DB_PATH`: SQLite file path
- `LOG_LEVEL`: logging level

## Notes

- This version is optimized for private chat verification.
- Group onboarding can be built on top of the same verification store.
- If the bot token is invalid, Telegram returns `401 Unauthorized`.


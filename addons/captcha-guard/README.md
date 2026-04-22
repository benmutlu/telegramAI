# captcha-guard

Image captcha verification for private Telegram bot chats.

`captcha-guard` is the first addon in Telegram Addon Studio. It is designed for a simple but useful problem: before a user can interact normally with a Telegram bot in private chat, the user must pass an image-based captcha challenge.

This helps reduce low-effort automated abuse, scripted probing, and repeated spam attempts in early bot conversations.

## What it does

When a user opens a private chat with the bot:

1. The bot creates a 6-character image captcha.
2. The user must send the code shown in the image.
3. The bot verifies the answer.
4. The user is marked as verified if the answer is correct.
5. Failed attempts are counted.
6. Too many failures trigger a temporary lockout.

Verification state is stored in SQLite, so the addon can preserve state across restarts.

## Features

- 6-character image captcha
- Noise and line obfuscation
- SQLite-backed verification state
- Retry counting
- Temporary lockouts after repeated failures
- Simple command surface
- Self-hostable setup

## Commands

- `/start`: start the verification flow
- `/captcha`: generate and send a new captcha
- `/status`: show current verification state
- `/resetcaptcha`: clear current state and restart verification

## How it works internally

The addon has three main responsibilities:

1. Generate captcha images
2. Store verification state per Telegram user
3. Enforce verification rules before normal access

The current implementation stores:

- Telegram user ID
- Telegram username
- whether the user is verified
- current captcha answer
- attempt count
- captcha creation time
- lockout time

## Intended use

This addon is currently optimized for:

- private chat onboarding
- early-message verification
- lightweight anti-spam protection

It is a good fit when you want a fast, self-hosted verification step before a user reaches the rest of your bot flow.

## What it is not yet

This addon does not yet provide:

- group join verification
- admin dashboard
- webhook/API mode
- provider integrations such as reCAPTCHA or Turnstile
- analytics or audit dashboards

Those can be added in future versions or as separate addons built on the same patterns.

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

Environment variables:

- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather
- `CAPTCHA_TTL_SECONDS`: how long a captcha remains valid
- `MAX_ATTEMPTS`: wrong answers allowed before lockout
- `LOCKOUT_SECONDS`: how long a user stays locked out
- `DB_PATH`: SQLite database path
- `LOG_LEVEL`: logging level

Example:

```env
TELEGRAM_BOT_TOKEN=123456789:YOUR_BOT_TOKEN
CAPTCHA_TTL_SECONDS=180
MAX_ATTEMPTS=3
LOCKOUT_SECONDS=600
DB_PATH=./captcha_guard.sqlite3
LOG_LEVEL=INFO
```

## User flow

Expected user experience:

1. User opens a private chat with the bot.
2. User sends `/start`.
3. Bot returns an image captcha.
4. User sends the code from the image.
5. Bot marks the user as verified on success.
6. Bot rejects repeated wrong answers and locks the user after the configured limit.

## Operating expectations

You should expect this addon to:

- work as a standalone verification layer
- keep local state in SQLite
- be easy to modify for custom Telegram flows

You should not expect it to:

- stop every sophisticated attacker
- replace enterprise anti-abuse systems
- solve group moderation by itself

This is a focused first layer, not a complete trust system.

## Development notes

- The bot currently uses long polling.
- State is persisted in SQLite.
- Captcha images are generated locally with Pillow.
- The implementation is intentionally small and readable.

## Future directions

Likely improvements for future versions:

- group verification mode
- inline refresh buttons
- stricter rate limiting
- provider-backed captcha options
- external API mode for third-party Telegram bots
- shared dashboard integration with future studio addons

## Troubleshooting

- `401 Unauthorized` usually means the Telegram bot token is invalid.
- If the bot starts but users never receive replies, check that you are messaging the correct bot in private chat.
- If captcha state is not persisting, verify that `DB_PATH` points to a writable location.


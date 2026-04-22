# keyword-router

Keyword-based message routing for Telegram private chats.

`keyword-router` is a lightweight Telegram addon that inspects incoming private messages, matches them against configurable keyword groups, and returns a route-specific reply. It can be used as a first layer for triage, sales intake, support routing, or basic classification before a human or a larger bot flow takes over.

## What it does

When a user sends a message in private chat:

1. The bot normalizes the message.
2. The bot compares the text against configured keyword groups.
3. The first matching route is selected.
4. The bot returns the configured reply for that route.
5. The interaction is logged in SQLite for later review.

If no route matches, the bot returns a default fallback reply.

## Features

- configurable keyword routes
- route-specific replies
- fallback reply for unmatched messages
- SQLite logging for simple review
- self-hostable setup

## Commands

- `/start`: show an introduction
- `/routes`: list configured routes
- `/stats`: show simple route hit counts

## Setup

```bash
cd addons/keyword-router
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Configuration

- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather
- `DB_PATH`: SQLite database path
- `DEFAULT_REPLY`: reply used when no route matches
- `KEYWORD_RULES_JSON`: JSON object describing routes
- `LOG_LEVEL`: logging level

## Route format

`KEYWORD_RULES_JSON` should look like this:

```json
{
  "sales": {
    "keywords": ["price", "pricing", "buy", "plan"],
    "reply": "It sounds like a sales question."
  },
  "support": {
    "keywords": ["help", "issue", "bug"],
    "reply": "It sounds like a support request."
  }
}
```

## Intended use

This addon works best for:

- lead triage
- support pre-routing
- category-based first replies
- simple intent routing without an LLM

## Limitations

- matching is keyword-based, not semantic
- no admin dashboard yet
- no external webhook integration yet


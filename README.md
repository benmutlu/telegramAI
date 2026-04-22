# Telegram Addon Studio

Open-source Telegram bot addons, shipped one product at a time.

This repository is a small product studio for Telegram automation and bot extensions. The goal is simple: ship one polished addon, document it properly, and keep the catalog growing on a daily cadence.

## What lives here

- `addons/`: production-ready Telegram addons
- `templates/`: starter kits for the next addon
- `scripts/`: tooling to spin up a new addon quickly
- `docs/`: studio vision, roadmap, and release process

## Today

Today's release is [`captcha-guard`](./addons/captcha-guard/README.md), a private-chat verification bot with image captchas, retry limits, lockouts, and SQLite-backed session state.

## Studio promise

- Ship small, useful Telegram products
- Keep the code readable and reusable
- Write docs that make self-hosting easy
- Publish in public and improve in public

## Addon catalog

| Addon | Status | Summary |
| --- | --- | --- |
| `captcha-guard` | Released | Image captcha verification for private Telegram bot chats |

## Quick start

```bash
cd addons/captcha-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Daily shipping workflow

1. Pick the next small Telegram addon problem.
2. Create a new addon from the template.
3. Build the MVP with docs, config, and examples.
4. Release it into `addons/`.
5. Update the catalog and roadmap.

## Open source stance

This repo is meant to stay public-friendly: lightweight dependencies, plain documentation, and a structure that can scale from hobby projects to hosted products.

## Credits

Built as a product studio workspace for Ben Mutlu, with Codex acting as the implementation partner for fast daily shipping.


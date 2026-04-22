# Telegram Addon Studio

Open-source Telegram addons, released as small standalone products.

Telegram Addon Studio is a public repository for building and documenting reusable Telegram bot extensions. Instead of keeping ideas as one-off scripts, this repo turns them into structured, self-hostable addons with setup instructions, predictable configuration, and a clear roadmap.

The long-term goal is to ship one Telegram-focused addon at a time, keep each release narrow and practical, and build a catalog of open-source components that can eventually evolve into larger products, hosted services, or SDKs.

## What this repository is

This repository is:

- A product studio for Telegram bot tooling
- A catalog of focused addons
- A reusable structure for shipping future Telegram products quickly
- A public documentation trail for how each addon works

This repository is not:

- A single monolithic Telegram bot
- A finished SaaS platform
- A plug-and-play marketplace yet

Each addon is intentionally small, independent, and documented as its own product.

## Repository structure

```text
addons/      Production-ready Telegram addons
docs/        Studio-level documentation, roadmap, and process
scripts/     Small utilities for creating new addons
templates/   Starter template for the next addon
```

## Current release

The first shipped addon is [`captcha-guard`](./addons/captcha-guard/README.md).

`captcha-guard` is a private-chat verification bot for Telegram. It sends an image captcha, validates the user's answer, tracks failed attempts in SQLite, and temporarily locks the user after too many failures.

## How the studio works

The studio follows a repeatable release loop:

1. Identify a narrow Telegram use case worth productizing.
2. Create a dedicated addon folder.
3. Build the smallest useful version.
4. Add configuration, docs, and example setup.
5. Ship it publicly.
6. Move on to the next addon while keeping the catalog coherent.

This keeps the repo practical. Every addon should be understandable in isolation, but the patterns should also compound over time.

## Addon expectations

Every addon in this repository should aim to have:

- A clear problem statement
- A README with setup and configuration instructions
- Safe defaults
- Minimal, explainable dependencies
- Honest notes about scope and limitations
- A path for future improvements

If an addon is too large, it should be split into layers or moved into its own dedicated repository later.

## Addon catalog

| Addon | Status | Summary |
| --- | --- | --- |
| `captcha-guard` | Released | Image-based private chat verification with retry limits and lockouts |

## Getting started

If you want to run the current addon immediately:

```bash
cd addons/captcha-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Then open `.env`, add your Telegram bot token from BotFather, and start a private chat with the bot.

## How each addon is expected to work

The working model for addons in this repository is:

- One addon solves one Telegram problem well
- Addons can be self-hosted
- Addons can eventually become API-backed products
- Shared patterns should migrate into common building blocks over time

Examples of future evolution:

- A moderation addon may later share a common storage layer
- A verification addon may later expose an API mode for third-party bots
- A routing addon may later plug into a shared dashboard

## Public open-source direction

This repository is being shaped to work well in public:

- English-first documentation
- Simple local setup
- No secrets committed
- Clean folder structure
- Small, composable releases

The intention is to make the repository readable both for users who want to self-host a tool and for developers who want to contribute new addons.

## Daily release direction

The broader idea behind Telegram Addon Studio is consistent shipping. The repository is meant to grow through frequent releases, where each addon is fully documented instead of half-finished and hidden in a private folder.

Planned categories include:

- verification
- moderation
- onboarding
- routing
- lead collection
- broadcast tooling
- safety and anti-abuse helpers

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution rules and the expected quality bar.

## Roadmap

See [docs/roadmap.md](./docs/roadmap.md) for upcoming addons and shared platform ideas.

## Vision

See [docs/vision.md](./docs/vision.md) for the long-term direction of the studio.

## License

MIT, see [LICENSE](./LICENSE).


# Contributing

Thanks for contributing to Telegram Addon Studio.

The goal of this repository is not just to collect code, but to ship addons that feel complete enough to be reused, tested, and understood by other people.

## Contribution principles

- Keep each addon focused
- Prefer small, understandable implementations
- Write docs as if the repo is public, because it is
- Do not commit secrets
- Be honest about limitations and scope

## Adding a new addon

1. Run `python scripts/new_addon.py <addon-name>`.
2. Define the narrowest useful version of the addon.
3. Add setup instructions and configuration examples.
4. Document how it works and what it does not do.
5. Update the root README catalog.
6. Update `docs/roadmap.md` if the roadmap should change.

## Quality bar

Each addon should have:

- a clear README
- a minimal working setup
- sane defaults
- explicit configuration
- readable code
- realistic expectations


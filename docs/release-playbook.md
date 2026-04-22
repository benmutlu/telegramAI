# Release Playbook

This document describes the expected release pattern for new Telegram addons in this repository.

## Release flow

1. Choose one Telegram problem worth solving.
2. Keep the first version as small as possible.
3. Build the addon in its own directory.
4. Add configuration, setup, and operating notes.
5. Verify that the addon runs locally.
6. Update the root catalog and roadmap.
7. Publish the work in a clean, documented state.

## Current cadence

The current studio cadence is two new addon releases per day. Each daily cycle should leave the public repository in a state where visitors can clearly see the two new additions in the catalog, documentation, and commit history.

## Minimum bar for release

- runnable from a fresh checkout
- documented configuration
- no secrets in the repository
- clear explanation of purpose
- clear explanation of current limits

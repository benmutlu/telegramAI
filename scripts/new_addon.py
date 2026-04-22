#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Addon name cannot be empty.")
    return slug


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/new_addon.py <addon-name>")
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    addons_dir = repo_root / "addons"
    addon_slug = slugify(sys.argv[1])
    addon_dir = addons_dir / addon_slug

    if addon_dir.exists():
        print(f"Addon already exists: {addon_dir}")
        return 1

    addon_dir.mkdir(parents=True)
    readme = addon_dir / "README.md"
    env_file = addon_dir / ".env.example"

    readme.write_text(
        f"# {addon_slug}\n\n"
        "Describe the addon here.\n\n"
        "## Setup\n\n"
        "Add setup instructions.\n",
        encoding="utf-8",
    )
    env_file.write_text("# Addon configuration goes here\n", encoding="utf-8")

    print(f"Created {addon_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


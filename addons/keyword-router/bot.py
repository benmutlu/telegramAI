#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
)
LOGGER = logging.getLogger("keyword_router")


def _required_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required setting: {key}")
    return value


@dataclass
class RouteConfig:
    keywords: list[str]
    reply: str


@dataclass
class Config:
    bot_token: str
    db_path: str
    default_reply: str
    routes: dict[str, RouteConfig]

    @classmethod
    def from_env(cls) -> "Config":
        raw_routes = json.loads(_required_env("KEYWORD_RULES_JSON"))
        routes: dict[str, RouteConfig] = {}
        for route_name, route_data in raw_routes.items():
            routes[route_name] = RouteConfig(
                keywords=[str(keyword).lower() for keyword in route_data.get("keywords", [])],
                reply=str(route_data.get("reply", "")).strip(),
            )

        return cls(
            bot_token=_required_env("TELEGRAM_BOT_TOKEN"),
            db_path=os.getenv("DB_PATH", "./keyword_router.sqlite3"),
            default_reply=os.getenv(
                "DEFAULT_REPLY",
                "Thanks for reaching out. A team member will follow up shortly.",
            ).strip(),
            routes=routes,
        )


class RouterStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS route_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    route_name TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def log_route(self, user_id: int, username: str | None, route_name: str, message_text: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO route_logs (user_id, username, route_name, message_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, route_name, message_text, int(time.time())),
            )
            conn.commit()

    def get_route_counts(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT route_name, COUNT(*) AS hit_count
                FROM route_logs
                GROUP BY route_name
                ORDER BY hit_count DESC, route_name ASC
                """
            ).fetchall()


class KeywordRouterService:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.store = RouterStore(config.db_path)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            "Keyword Router is active.\n"
            "Send a private message and I will classify it using the configured routes."
        )

    async def routes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        lines = ["Configured routes:"]
        for route_name, route in sorted(self.config.routes.items()):
            lines.append(f"- {route_name}: {', '.join(route.keywords)}")
        await update.message.reply_text("\n".join(lines))

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        rows = self.store.get_route_counts()
        if not rows:
            await update.message.reply_text("No route hits recorded yet.")
            return

        lines = ["Route stats:"]
        for row in rows:
            lines.append(f"- {row['route_name']}: {row['hit_count']}")
        await update.message.reply_text("\n".join(lines))

    def _match_route(self, message_text: str) -> tuple[str, str]:
        normalized = message_text.lower()
        for route_name, route in self.config.routes.items():
            for keyword in route.keywords:
                if keyword and keyword in normalized:
                    return route_name, route.reply
        return "fallback", self.config.default_reply

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        if not update.effective_chat or update.effective_chat.type != "private":
            return

        route_name, reply = self._match_route(update.message.text)
        user = update.effective_user
        self.store.log_route(
            user_id=user.id if user else 0,
            username=user.username if user else None,
            route_name=route_name,
            message_text=update.message.text,
        )
        await update.message.reply_text(reply)


def main() -> None:
    asyncio.set_event_loop(asyncio.new_event_loop())
    config = Config.from_env()
    service = KeywordRouterService(config)

    application = Application.builder().token(config.bot_token).build()
    application.add_handler(CommandHandler("start", service.start))
    application.add_handler(CommandHandler("routes", service.routes))
    application.add_handler(CommandHandler("stats", service.stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.handle_message))

    LOGGER.info("keyword-router starting")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


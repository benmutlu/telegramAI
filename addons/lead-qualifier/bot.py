#!/usr/bin/env python3
from __future__ import annotations

import asyncio
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
LOGGER = logging.getLogger("lead_qualifier")


def _required_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required setting: {key}")
    return value


@dataclass
class Config:
    bot_token: str
    db_path: str
    intro_message: str
    success_message: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bot_token=_required_env("TELEGRAM_BOT_TOKEN"),
            db_path=os.getenv("DB_PATH", "./lead_qualifier.sqlite3"),
            intro_message=os.getenv(
                "INTRO_MESSAGE",
                "Welcome. I will ask a few short questions to capture your inquiry.",
            ).strip(),
            success_message=os.getenv(
                "SUCCESS_MESSAGE",
                "Thanks. Your responses have been recorded and the team can review them.",
            ).strip(),
        )


class LeadStore:
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
                CREATE TABLE IF NOT EXISTS conversation_state (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    current_step TEXT,
                    name TEXT,
                    company TEXT,
                    email TEXT,
                    need TEXT,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lead_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    name TEXT NOT NULL,
                    company TEXT NOT NULL,
                    email TEXT NOT NULL,
                    need TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def get_state(self, user_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM conversation_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    def begin_flow(self, user_id: int, username: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_state (user_id, username, current_step, name, company, email, need, updated_at)
                VALUES (?, ?, 'name', NULL, NULL, NULL, NULL, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    current_step = 'name',
                    name = NULL,
                    company = NULL,
                    email = NULL,
                    need = NULL,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, int(time.time())),
            )
            conn.commit()

    def update_step(self, user_id: int, field_name: str, value: str, next_step: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE conversation_state
                SET {field_name} = ?, current_step = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (value, next_step, int(time.time()), user_id),
            )
            conn.commit()

    def complete_submission(self, user_id: int, username: str | None) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, company, email, need FROM conversation_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                raise RuntimeError("No active conversation found.")

            conn.execute(
                """
                INSERT INTO lead_submissions (user_id, username, name, company, email, need, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    row["name"],
                    row["company"],
                    row["email"],
                    row["need"],
                    int(time.time()),
                ),
            )
            conn.execute("DELETE FROM conversation_state WHERE user_id = ?", (user_id,))
            conn.commit()

    def clear_state(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM conversation_state WHERE user_id = ?", (user_id,))
            conn.commit()

    def latest_submission(self, user_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM lead_submissions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()


class LeadQualifierService:
    QUESTIONS = {
        "name": "What is your name?",
        "company": "What company are you with?",
        "email": "What email should the team use to reach you?",
        "need": "What do you need help with?",
    }

    def __init__(self, config: Config) -> None:
        self.config = config
        self.store = LeadStore(config.db_path)

    def _user_identity(self, update: Update) -> tuple[int, str | None] | None:
        if not update.effective_user:
            return None
        return update.effective_user.id, update.effective_user.username

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        identity = self._user_identity(update)
        if not identity:
            return
        user_id, username = identity
        self.store.begin_flow(user_id, username)
        await update.message.reply_text(self.config.intro_message)
        await update.message.reply_text(self.QUESTIONS["name"])

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        identity = self._user_identity(update)
        if not identity:
            return
        user_id, _username = identity
        state = self.store.get_state(user_id)
        if state:
            await update.message.reply_text(f"Current step: {state['current_step']}")
            return

        latest = self.store.latest_submission(user_id)
        if latest:
            await update.message.reply_text(
                f"Last submission recorded for {latest['name']} at {latest['email']}."
            )
            return

        await update.message.reply_text("No active or completed submission found yet.")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        identity = self._user_identity(update)
        if not identity:
            return
        user_id, username = identity
        self.store.clear_state(user_id)
        self.store.begin_flow(user_id, username)
        await update.message.reply_text("The intake flow has been reset.")
        await update.message.reply_text(self.QUESTIONS["name"])

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        if not update.effective_chat or update.effective_chat.type != "private":
            return

        identity = self._user_identity(update)
        if not identity:
            return
        user_id, username = identity
        state = self.store.get_state(user_id)
        if not state:
            self.store.begin_flow(user_id, username)
            await update.message.reply_text(self.config.intro_message)
            await update.message.reply_text(self.QUESTIONS["name"])
            return

        current_step = state["current_step"]
        message_text = update.message.text.strip()
        if not current_step:
            await update.message.reply_text("The flow is complete. Use /start to submit a new inquiry.")
            return

        if current_step == "name":
            self.store.update_step(user_id, "name", message_text, "company")
            await update.message.reply_text(self.QUESTIONS["company"])
            return

        if current_step == "company":
            self.store.update_step(user_id, "company", message_text, "email")
            await update.message.reply_text(self.QUESTIONS["email"])
            return

        if current_step == "email":
            self.store.update_step(user_id, "email", message_text, "need")
            await update.message.reply_text(self.QUESTIONS["need"])
            return

        if current_step == "need":
            self.store.update_step(user_id, "need", message_text, None)
            self.store.complete_submission(user_id, username)
            await update.message.reply_text(self.config.success_message)
            return


def main() -> None:
    asyncio.set_event_loop(asyncio.new_event_loop())
    config = Config.from_env()
    service = LeadQualifierService(config)

    application = Application.builder().token(config.bot_token).build()
    application.add_handler(CommandHandler("start", service.start))
    application.add_handler(CommandHandler("status", service.status))
    application.add_handler(CommandHandler("reset", service.reset))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.handle_message))

    LOGGER.info("lead-qualifier starting")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


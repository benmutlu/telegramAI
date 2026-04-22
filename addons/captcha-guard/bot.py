#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import io
import logging
import os
import random
import sqlite3
import string
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
)
LOGGER = logging.getLogger("captcha_guard")


def _required_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Missing required setting: {key}")
    return value


@dataclass
class Config:
    bot_token: str
    captcha_ttl_seconds: int
    max_attempts: int
    lockout_seconds: int
    db_path: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bot_token=_required_env("TELEGRAM_BOT_TOKEN"),
            captcha_ttl_seconds=int(os.getenv("CAPTCHA_TTL_SECONDS", "180")),
            max_attempts=int(os.getenv("MAX_ATTEMPTS", "3")),
            lockout_seconds=int(os.getenv("LOCKOUT_SECONDS", "600")),
            db_path=os.getenv("DB_PATH", "./captcha_guard.sqlite3"),
        )


class VerificationStore:
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
                CREATE TABLE IF NOT EXISTS verification_state (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    verified INTEGER NOT NULL DEFAULT 0,
                    current_answer TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    captcha_created_at INTEGER,
                    lock_until INTEGER,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM verification_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    def upsert_captcha(self, user_id: int, username: str | None, answer: str, created_at: int) -> None:
        existing = self.get_user(user_id)
        attempts = int(existing["attempts"]) if existing else 0
        lock_until = int(existing["lock_until"]) if existing and existing["lock_until"] else None

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO verification_state (
                    user_id, username, verified, current_answer, attempts,
                    captcha_created_at, lock_until, updated_at
                ) VALUES (?, ?, 0, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    verified = 0,
                    current_answer = excluded.current_answer,
                    attempts = ?,
                    captcha_created_at = excluded.captcha_created_at,
                    lock_until = ?,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    username,
                    answer,
                    attempts,
                    created_at,
                    lock_until,
                    created_at,
                    attempts,
                    lock_until,
                ),
            )
            conn.commit()

    def mark_verified(self, user_id: int, username: str | None) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO verification_state (
                    user_id, username, verified, current_answer, attempts,
                    captcha_created_at, lock_until, updated_at
                ) VALUES (?, ?, 1, NULL, 0, NULL, NULL, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    verified = 1,
                    current_answer = NULL,
                    attempts = 0,
                    captcha_created_at = NULL,
                    lock_until = NULL,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, now),
            )
            conn.commit()

    def register_failure(self, user_id: int, username: str | None, lock_until: int | None) -> int:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO verification_state (
                    user_id, username, verified, current_answer, attempts,
                    captcha_created_at, lock_until, updated_at
                ) VALUES (?, ?, 0, NULL, 1, NULL, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    verified = 0,
                    attempts = attempts + 1,
                    lock_until = ?,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, lock_until, now, lock_until),
            )
            conn.commit()

            row = conn.execute(
                "SELECT attempts FROM verification_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return int(row["attempts"])

    def reset_user(self, user_id: int, username: str | None) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO verification_state (
                    user_id, username, verified, current_answer, attempts,
                    captcha_created_at, lock_until, updated_at
                ) VALUES (?, ?, 0, NULL, 0, NULL, NULL, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    verified = 0,
                    current_answer = NULL,
                    attempts = 0,
                    captcha_created_at = NULL,
                    lock_until = NULL,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, now),
            )
            conn.commit()

    def set_lockout(self, user_id: int, username: str | None, lock_until: int) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO verification_state (
                    user_id, username, verified, current_answer, attempts,
                    captcha_created_at, lock_until, updated_at
                ) VALUES (?, ?, 0, NULL, 0, NULL, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    verified = 0,
                    current_answer = NULL,
                    attempts = 0,
                    captcha_created_at = NULL,
                    lock_until = excluded.lock_until,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, lock_until, now),
            )
            conn.commit()


class CaptchaGuardService:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.store = VerificationStore(config.db_path)

    @staticmethod
    def _new_captcha() -> dict[str, int | str | bytes]:
        code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        return {
            "answer": code,
            "created_at": int(time.time()),
            "image_bytes": CaptchaGuardService._render_captcha_image(code),
        }

    @staticmethod
    def _render_captcha_image(code: str) -> bytes:
        width = 320
        height = 120
        image = Image.new("RGB", (width, height), (245, 247, 250))
        draw = ImageDraw.Draw(image)

        for _ in range(700):
            draw.point(
                (random.randint(0, width - 1), random.randint(0, height - 1)),
                fill=CaptchaGuardService._random_color(120, 220),
            )

        for _ in range(12):
            start = (random.randint(0, width), random.randint(0, height))
            end = (random.randint(0, width), random.randint(0, height))
            draw.line(
                [start, end],
                fill=CaptchaGuardService._random_color(80, 180),
                width=random.randint(1, 3),
            )

        char_width = width // (len(code) + 1)
        for index, char in enumerate(code):
            layer = Image.new("RGBA", (80, 100), (255, 255, 255, 0))
            layer_draw = ImageDraw.Draw(layer)
            font = CaptchaGuardService._load_font(random.randint(38, 52))
            layer_draw.text(
                (18, 20),
                char,
                font=font,
                fill=CaptchaGuardService._random_color(20, 110),
            )
            rotated = layer.rotate(
                random.randint(-28, 28),
                resample=Image.Resampling.BICUBIC,
                expand=1,
            )
            image.paste(
                rotated,
                (10 + index * char_width + random.randint(0, 18), random.randint(8, 28)),
                rotated,
            )

        image = image.filter(ImageFilter.GaussianBlur(radius=0.6))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        font_candidates = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
            "/System/Library/Fonts/Supplemental/Verdana.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()

    @staticmethod
    def _random_color(low: int, high: int) -> tuple[int, int, int]:
        return (
            random.randint(low, high),
            random.randint(low, high),
            random.randint(low, high),
        )

    def _get_identity(self, update: Update) -> tuple[int, str | None] | None:
        if not update.effective_user:
            return None
        return update.effective_user.id, update.effective_user.username

    def _get_state(self, user_id: int) -> sqlite3.Row | None:
        return self.store.get_user(user_id)

    def _is_locked(self, state: sqlite3.Row | None) -> tuple[bool, int]:
        now = int(time.time())
        if not state or not state["lock_until"]:
            return False, 0
        remaining = int(state["lock_until"]) - now
        return remaining > 0, max(remaining, 0)

    def _is_verified(self, state: sqlite3.Row | None) -> bool:
        return bool(state and int(state["verified"]) == 1)

    def _captcha_expired(self, state: sqlite3.Row | None) -> bool:
        if not state or not state["captcha_created_at"]:
            return True
        return (int(time.time()) - int(state["captcha_created_at"])) > self.config.captcha_ttl_seconds

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.type != "private" or not update.message:
            return

        identity = self._get_identity(update)
        if not identity:
            return
        user_id, username = identity
        state = self._get_state(user_id)

        if self._is_verified(state):
            await update.message.reply_text("Already verified.")
            return

        locked, remaining = self._is_locked(state)
        if locked:
            await update.message.reply_text(f"Locked. Try again in {remaining}s.")
            return

        await self._send_new_captcha(update, user_id, username)

    async def captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.type != "private" or not update.message:
            return

        identity = self._get_identity(update)
        if not identity:
            return
        user_id, username = identity
        state = self._get_state(user_id)

        if self._is_verified(state):
            await update.message.reply_text("Already verified.")
            return

        locked, remaining = self._is_locked(state)
        if locked:
            await update.message.reply_text(f"Locked. Try again in {remaining}s.")
            return

        await self._send_new_captcha(update, user_id, username)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.type != "private" or not update.message:
            return

        identity = self._get_identity(update)
        if not identity:
            return
        user_id, _username = identity
        state = self._get_state(user_id)

        if self._is_verified(state):
            await update.message.reply_text("Status: verified.")
            return

        locked, remaining = self._is_locked(state)
        if locked:
            await update.message.reply_text(f"Status: locked for {remaining}s.")
            return

        attempts = int(state["attempts"]) if state else 0
        await update.message.reply_text(f"Status: pending. Attempts: {attempts}/{self.config.max_attempts}.")

    async def _send_new_captcha(self, update: Update, user_id: int, username: str | None) -> None:
        if not update.message:
            return

        captcha = self._new_captcha()
        self.store.upsert_captcha(
            user_id=user_id,
            username=username,
            answer=str(captcha["answer"]),
            created_at=int(captcha["created_at"]),
        )
        await update.message.reply_photo(
            photo=io.BytesIO(captcha["image_bytes"]),
            caption=(
                "Verify first.\n"
                "Send the 6-character code from the image.\n"
                f"Expires in {self.config.captcha_ttl_seconds}s."
            ),
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.type != "private" or not update.message:
            return

        identity = self._get_identity(update)
        if not identity:
            return
        user_id, username = identity
        state = self._get_state(user_id)

        if self._is_verified(state):
            await update.message.reply_text("Verified.")
            return

        locked, remaining = self._is_locked(state)
        if locked:
            await update.message.reply_text(f"Locked. Try again in {remaining}s.")
            return

        if self._captcha_expired(state):
            await update.message.reply_text("Expired. New captcha sent.")
            await self._send_new_captcha(update, user_id, username)
            return

        message_text = update.message.text.strip()
        normalized_text = "".join(ch for ch in message_text.upper() if ch in string.ascii_uppercase + string.digits)
        if len(normalized_text) < 4:
            await update.message.reply_text("Send the code only.")
            return

        expected_answer = str(state["current_answer"]).upper() if state and state["current_answer"] else ""
        if normalized_text != expected_answer:
            next_attempt = int(state["attempts"]) + 1 if state else 1
            attempts = self.store.register_failure(
                user_id=user_id,
                username=username,
                lock_until=int(time.time()) + self.config.lockout_seconds
                if next_attempt >= self.config.max_attempts
                else None,
            )

            if attempts >= self.config.max_attempts:
                locked_until = int(time.time()) + self.config.lockout_seconds
                self.store.set_lockout(user_id, username, locked_until)
                await update.message.reply_text(f"Locked. Try again in {self.config.lockout_seconds}s.")
                return

            await update.message.reply_text("Wrong code. New captcha sent.")
            await self._send_new_captcha(update, user_id, username)
            return

        self.store.mark_verified(user_id, username)
        await update.message.reply_text("Verification complete.")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.type != "private" or not update.message:
            return
        identity = self._get_identity(update)
        if not identity:
            return
        user_id, username = identity
        self.store.reset_user(user_id, username)
        await self._send_new_captcha(update, user_id, username)


def main() -> None:
    asyncio.set_event_loop(asyncio.new_event_loop())
    config = Config.from_env()
    service = CaptchaGuardService(config)

    application = Application.builder().token(config.bot_token).build()
    application.add_handler(CommandHandler("start", service.start))
    application.add_handler(CommandHandler("captcha", service.captcha))
    application.add_handler(CommandHandler("status", service.status))
    application.add_handler(CommandHandler("resetcaptcha", service.reset))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.handle_message))

    LOGGER.info("captcha-guard starting")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

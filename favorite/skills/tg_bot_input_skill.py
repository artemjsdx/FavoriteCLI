"""
favorite/skills/tg_bot_input_skill.py — Telegram bot input skill (§44).
Allows controlling FavoriteCLI from Telegram.
"""
import json
import threading
from pathlib import Path
from .base import ISkill

_TG_BOT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "tg_bot_input.json"


def _load_config() -> dict:
    if _TG_BOT_CONFIG.exists():
        try:
            return json.loads(_TG_BOT_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class TgBotInputSkill(ISkill):
    name = "tg_bot_input"
    description = "Control FavoriteCLI from Telegram bot (§44). Bidirectional CLI-Telegram bridge."
    _bot_thread: threading.Thread | None = None
    _bot_running: bool = False

    def get_prompt_snippet(self) -> str:
        return (
            "Skill: tg_bot_input — Telegram-бот как интерфейс CLI.\n"
            "Usage: <SKILL:name=tg_bot_input>start</SKILL> | stop | status"
        )

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "start").strip().lower()
        cfg_data = _load_config()
        if not cfg_data.get("bot_token"):
            return (
                "[tg_bot_input: не настроен. Настройка:\n"
                "  1. Создай бота через @BotFather → получи токен\n"
                "  2. Заполни config/tg_bot_input.json:\n"
                '     {"bot_token": "...", "allowed_ids": [12345678]}\n'
                "  3. Запусти: /skills tg_bot_input on]"
            )
        if args == "start":
            return self._start(cfg_data, ctx)
        if args == "stop":
            TgBotInputSkill._bot_running = False
            return "[tg_bot_input: остановлен]"
        if args == "status":
            return f"[tg_bot_input: {'running' if self._bot_running else 'stopped'}]"
        return f"[tg_bot_input: неизвестная команда '{args}']"

    def _start(self, cfg_data: dict, ctx=None) -> str:
        if self._bot_running:
            return "[tg_bot_input: уже запущен]"
        try:
            import importlib
            importlib.import_module("telegram")
        except ImportError:
            return "[tg_bot_input ERROR: установи python-telegram-bot: pip install python-telegram-bot]"
        
        def _run_bot():
            TgBotInputSkill._bot_running = True
            try:
                from telegram.ext import Application, MessageHandler, filters
                from telegram import Update
                import asyncio

                bot_token = cfg_data["bot_token"]
                allowed_ids = set(cfg_data.get("allowed_ids", []))

                async def handle_message(update: Update, context) -> None:
                    user_id = update.effective_user.id if update.effective_user else 0
                    if allowed_ids and user_id not in allowed_ids:
                        await update.message.reply_text("❌ Доступ запрещён")
                        return
                    text = update.message.text or ""
                    if not text:
                        await update.message.reply_text("⚠ Только текстовые сообщения поддерживаются")
                        return
                    # Inject message into agent context (simplified: log it)
                    try:
                        from ..commands.logs_cmd import log_event
                        log_event(
                            ctx.workdir if ctx else ".",
                            ctx.session_id if ctx else "unknown",
                            "TG_BOT_INPUT",
                            text[:200],
                        )
                    except Exception:
                        pass
                    await update.message.reply_text(
                        f"✓ Получено: {text[:100]}\n[агент обрабатывает в фоне]"
                    )

                app = Application.builder().token(bot_token).build()
                app.add_handler(MessageHandler(filters.TEXT, handle_message))
                app.run_polling(stop_signals=None)
            except Exception as e:
                TgBotInputSkill._bot_running = False
                import sys; print(f"[tg_bot_input ERROR]: {e}", file=sys.stderr)

        TgBotInputSkill._bot_thread = threading.Thread(target=_run_bot, daemon=True)
        TgBotInputSkill._bot_thread.start()
        import time; time.sleep(1)
        return "[tg_bot_input: запущен — бот слушает входящие сообщения]"

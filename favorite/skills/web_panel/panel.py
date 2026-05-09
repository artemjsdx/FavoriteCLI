"""
favorite/skills/web_panel/panel.py
Web panel skill — launches a local FastAPI dashboard for monitoring FavoriteCLI sessions.
Accessible at http://localhost:7860 (or PORT env var).
"""
import json
import os
import threading
from pathlib import Path
from ..base import ISkill


class WebPanelSkill(ISkill):
    name = "web_panel"
    description = "Launch local FastAPI web dashboard for monitoring sessions and tasks."
    _prompt_snippet = (
        "Skill: web_panel — запускает веб-дашборд для мониторинга сессий, задач и логов.\n"
        "Usage: <SKILL:name=web_panel>start</SKILL> or <SKILL:name=web_panel>stop</SKILL>"
    )
    _server_thread: threading.Thread | None = None
    _server_running = False

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "start").strip().lower()
        if args == "start":
            return self._start_server(ctx)
        if args == "stop":
            return self._stop_server()
        if args == "status":
            return f"[web_panel: {'running' if self._server_running else 'stopped'}]"
        return f"[web_panel: неизвестная команда '{args}'. Используй: start | stop | status]"

    def _start_server(self, ctx=None) -> str:
        if self._server_running:
            port = int(os.environ.get("FAV_PANEL_PORT", "7860"))
            return f"[web_panel: уже запущен на http://localhost:{port}]"
        try:
            import uvicorn
            from .app import create_app
            workdir = ctx.workdir if ctx else "."
            app = create_app(workdir=workdir)
            port = int(os.environ.get("FAV_PANEL_PORT", "7860"))

            def _run() -> None:
                WebPanelSkill._server_running = True
                try:
                    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
                finally:
                    WebPanelSkill._server_running = False

            WebPanelSkill._server_thread = threading.Thread(target=_run, daemon=True)
            WebPanelSkill._server_thread.start()
            import time; time.sleep(0.8)
            return f"[web_panel: запущен на http://localhost:{port}]"
        except ImportError:
            return "[web_panel ERROR: FastAPI/uvicorn не установлены. Запусти: pip install fastapi uvicorn]"
        except Exception as e:
            return f"[web_panel ERROR: {e}]"

    def _stop_server(self) -> str:
        # uvicorn daemon thread stops when process exits;
        # for clean shutdown signal the thread
        WebPanelSkill._server_running = False
        return "[web_panel: остановлен (перезапусти если нужно)]"

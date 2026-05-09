"""
favorite/commands/auto_cmd.py — §19.1 /auto command.
Full autonomous loop menu: start/stop/pause/resume/status/settings.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_active_loop: Optional["_LoopHandle"] = None


class _LoopHandle:
    def __init__(self, loop, thread: threading.Thread) -> None:
        self.loop   = loop
        self.thread = thread
        self.result: Optional[str] = None

    @property
    def running(self) -> bool:
        return self.thread.is_alive()


# ── Public API used by app.py ──────────────────────────────────────────────

def is_auto_active() -> bool:
    return _active_loop is not None and _active_loop.running


def get_auto_stats():
    if _active_loop and _active_loop.loop:
        return _active_loop.loop.stats
    return None


def stop_auto() -> None:
    global _active_loop
    if _active_loop and _active_loop.loop:
        _active_loop.loop.stop()


def pause_auto() -> None:
    if _active_loop and _active_loop.loop:
        _active_loop.loop.pause()


def resume_auto() -> None:
    if _active_loop and _active_loop.loop:
        _active_loop.loop.resume()


# ── /auto command ──────────────────────────────────────────────────────────

def cmd_auto(args: list[str], ctx, cfg) -> None:
    """
    /auto [start|stop|pause|resume|status|settings] [message]

    Controls the autonomous loop (§19.1).
    Without arguments: shows menu.
    """
    global _active_loop

    sub = args[0].lower() if args else ""

    if sub in ("stop", "стоп", "s"):
        _cmd_stop()
    elif sub in ("pause", "пауза", "p"):
        _cmd_pause()
    elif sub in ("resume", "продолжить", "r"):
        _cmd_resume()
    elif sub in ("status", "статус"):
        _cmd_status()
    elif sub in ("settings", "настройки", "cfg"):
        _cmd_settings()
    elif sub in ("start", "старт", "") or not sub:
        task = " ".join(args[1:]) if args else ""
        _cmd_start(task, ctx, cfg)
    else:
        # Treat as inline task message
        task = " ".join(args)
        _cmd_start(task, ctx, cfg)


def _cmd_start(task: str, ctx, cfg) -> None:
    global _active_loop

    if is_auto_active():
        console.print("  [yellow]/auto уже запущен. Используй /auto stop для остановки.[/yellow]")
        return

    if not task:
        console.print()
        console.print("  [bold #ff8c00]Введи задачу для автономного выполнения:[/bold #ff8c00]")
        console.print("  [dim](или нажми Enter для продолжения последней задачи)[/dim]")
        try:
            task = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            return

    settings = _load_settings()
    max_steps       = settings.get("max_steps", 100)
    max_duration    = settings.get("max_duration_sec", 36000)
    mode_label      = settings.get("mode", "unified")

    try:
        from ..agent.auto_mode import AutoLoop
    except ImportError:
        console.print("  [red]auto_mode.py не найден. Обнови проект.[/red]")
        return

    def _make_send(ctx, cfg):
        def _send(msg: str):
            try:
                from ..agent.runner import run_agent_turn
                result = run_agent_turn(msg, ctx=ctx, cfg=cfg, is_auto=True)
                reply  = result.get("reply", "")
                tokens = result.get("tokens", 0)
                return reply, tokens
            except Exception as e:
                return f"[AGENT ERROR] {e}", 0
        return _send

    def _make_execute(ctx):
        def _execute(reply: str, stats):
            try:
                from ..agent.executor import process_response
                results = process_response(reply, ctx=ctx, cfg=None)
                wait_user = "__WAIT_USER__" in (results or "")
                return results, wait_user
            except Exception as e:
                return f"[EXECUTE ERROR] {e}", False
        return _execute

    loop = AutoLoop(
        send_to_agent = _make_send(ctx, cfg),
        execute_tags  = _make_execute(ctx),
        cfg           = cfg,
        workdir       = ctx.workdir,
        session_id    = ctx.session_id,
        mode_label    = mode_label,
    )

    def _run():
        r = loop.run(
            initial_message=task,
            max_steps=max_steps,
            max_duration_sec=max_duration,
        )
        _active_loop.result = r  # type: ignore
        console.print(f"\n  [dim #888888]/auto завершён: {r}[/dim #888888]")

    thread = threading.Thread(target=_run, daemon=True, name="auto-loop")
    _active_loop = _LoopHandle(loop, thread)
    thread.start()

    console.print(f"  [bold #ff8c00]✓ /auto запущен[/bold #ff8c00]  задача: [dim]{escape(task[:80])}[/dim]")
    console.print(f"  [dim]Лимиты: {max_steps} шагов / {max_duration//3600}ч  |  /auto stop для остановки[/dim]")


def _cmd_stop() -> None:
    global _active_loop
    if not is_auto_active():
        console.print("  [dim]/auto не запущен.[/dim]")
        return
    stop_auto()
    console.print("  [dim #888888]✓ /auto остановлен[/dim #888888]")
    _active_loop = None


def _cmd_pause() -> None:
    if not is_auto_active():
        console.print("  [dim]/auto не запущен.[/dim]")
        return
    pause_auto()
    console.print("  [dim #888888]⏸ /auto на паузе. /auto resume для продолжения[/dim #888888]")


def _cmd_resume() -> None:
    if not _active_loop:
        console.print("  [dim]Нет активного /auto.[/dim]")
        return
    resume_auto()
    console.print("  [dim #888888]▶ /auto возобновлён[/dim #888888]")


def _cmd_status() -> None:
    if not _active_loop:
        console.print("  [dim #888888]/auto: не активен[/dim #888888]")
        return
    stats = get_auto_stats()
    if not stats:
        console.print("  [dim #888888]/auto: нет данных[/dim #888888]")
        return
    table = Table(box=None, padding=(0, 2), show_header=False)
    table.add_column("K", style="dim")
    table.add_column("V", style="#ff8c00")
    table.add_row("Статус",    "⏸ пауза" if stats.paused else "▶ активен")
    table.add_row("Шаг",       str(stats.step))
    table.add_row("Время",     stats.elapsed_str)
    table.add_row("~Токенов",  f"{stats.total_tokens:,}")
    table.add_row("Жив",       str(_active_loop.running))
    console.print()
    console.print(Panel(table, title="[bold #ff8c00]/auto статус[/bold #ff8c00]", border_style="#ff8c00"))


def _cmd_settings() -> None:
    settings = _load_settings()
    console.print()
    console.print(Panel(
        _fmt_settings(settings),
        title="[bold #ff8c00]/auto настройки[/bold #ff8c00]",
        subtitle="[dim]key=value для изменения | q выход[/dim]",
        border_style="#ff8c00",
    ))
    while True:
        try:
            raw = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if raw.lower() in ("q", ""):
            break
        if "=" in raw:
            k, _, v = raw.partition("=")
            k = k.strip(); v = v.strip()
            if k == "max_steps":
                settings["max_steps"] = int(v)
            elif k == "max_duration_sec":
                settings["max_duration_sec"] = int(v)
            elif k == "mode":
                settings["mode"] = v
            else:
                console.print(f"  [dim]Неизвестный ключ: {k}[/dim]")
                continue
            _save_settings(settings)
            console.print(f"  [dim #888888]✓ {k}={v}[/dim #888888]")


def _fmt_settings(s: dict) -> str:
    return (
        f"  max_steps       = [cyan]{s.get('max_steps', 100)}[/cyan]\n"
        f"  max_duration_sec= [cyan]{s.get('max_duration_sec', 36000)}[/cyan]  "
        f"([dim]{s.get('max_duration_sec', 36000)//3600}ч[/dim])\n"
        f"  mode            = [cyan]{s.get('mode', 'hybrid')}[/cyan]  "
        f"[dim](unified|independent|hybrid)[/dim]"
    )


def _load_settings() -> dict:
    f = _CONFIG_DIR / "auto_settings.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"max_steps": 100, "max_duration_sec": 36000, "mode": "hybrid"}


def _save_settings(data: dict) -> None:
    f = _CONFIG_DIR / "auto_settings.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class AutoCommand(ICommand):
    name = "/auto"
    description = "Автономный цикл агента — запуск/стоп/пауза/статус/настройки"
    priority = 10

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_auto(arg_list, ctx, getattr(ctx, "config", None))

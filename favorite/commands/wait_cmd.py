"""
favorite/commands/wait_cmd.py — §19.2 /wait command.
Blocks new autonomous tick until all background sub-agents finish.
"""
from __future__ import annotations

import time
import json
from pathlib import Path
from rich.live import Live
from rich.text import Text
from rich.console import Console

console = Console()


def cmd_wait(args: list[str], ctx, cfg) -> None:
    """
    /wait [timeout_sec]

    Pauses autonomous loop until all background sub-agents complete
    or until optional timeout expires.
    """
    timeout_sec = 300  # default 5 min
    if args:
        try:
            timeout_sec = int(args[0])
        except ValueError:
            pass

    sess_dir = Path(ctx.workdir) / "sessions" / ctx.session_id
    subs_file = sess_dir / "active_subs.json"

    deadline = time.time() + timeout_sec
    interval = 2.0

    with Live(console=console, refresh_per_second=2) as live:
        while time.time() < deadline:
            pending = _get_pending_subs(subs_file)
            if not pending:
                live.update(Text("  ✓ Все фоновые суб-агенты завершились.", style="dim #888888"))
                time.sleep(0.5)
                break

            names = ", ".join(s.get("id", "?") for s in pending[:5])
            extra = f" (+{len(pending)-5})" if len(pending) > 5 else ""
            live.update(Text(
                f"  ⏳ Жду {len(pending)} фоновых: {names}{extra}  [{int(deadline-time.time())}с осталось]",
                style="#ff8c00"
            ))
            time.sleep(interval)
        else:
            console.print(f"  [dim #888888]/wait: таймаут {timeout_sec}с — продолжаю[/dim #888888]")


def _get_pending_subs(subs_file: Path) -> list[dict]:
    if not subs_file.exists():
        return []
    try:
        data = json.loads(subs_file.read_text(encoding="utf-8"))
        return [s for s in data if s.get("status") not in ("done", "error", "cancelled")]
    except Exception:
        return []


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class WaitCommand(ICommand):
    name = "/wait"
    description = "Ждать завершения всех фоновых суб-агентов"
    priority = 25

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_wait(arg_list, ctx, getattr(ctx, "config", None))

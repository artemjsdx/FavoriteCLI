"""
favorite/commands/subs_cmd.py — /subs command.

Shows table of all sub-agents across all main agents.
§19.1 sub-agent management UI.
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .base import ICommand, CommandContext

console = Console()
_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_active_subs() -> list[dict]:
    """Collect running sub-agents from sessions."""
    subs = []
    subs_dir = _ROOT / "sessions"
    if not subs_dir.exists():
        return subs
    for session_dir in sorted(subs_dir.iterdir()):
        subs_file = session_dir / "subs.jsonl"
        if not subs_file.exists():
            continue
        try:
            for line in subs_file.read_text("utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    entry["session"] = session_dir.name[:8]
                    subs.append(entry)
        except Exception:
            continue
    return subs


class SubsCommand(ICommand):
    name = "/subs"
    description = "Таблица суб-агентов всех мейнов"

    def execute(self, args: list[str], ctx: CommandContext, cfg) -> None:
        filter_main = args[0] if args else None

        # Попытка получить активных субов из контекста
        active_subs = []
        if hasattr(ctx, "sub_agents") and ctx.sub_agents:
            for name, info in ctx.sub_agents.items():
                active_subs.append({
                    "name": name,
                    "main": getattr(ctx, "leading_agent", "main-1"),
                    "status": info.get("status", "active"),
                    "role": info.get("role", "—"),
                    "ticks": info.get("ticks", 0),
                    "model": info.get("model", "—"),
                    "session": getattr(ctx, "session_id", "")[:8],
                })

        # Дополнительно из файлов сессий
        active_subs.extend(_load_active_subs())

        if filter_main:
            active_subs = [s for s in active_subs if filter_main in s.get("main", "")]

        if not active_subs:
            console.print(f"  [dim]Нет активных суб-агентов{' для ' + filter_main if filter_main else ''}.[/dim]")
            return

        table = Table(
            title=f"[bold #ff8c00]Суб-агенты[/bold #ff8c00]" + (f" [{filter_main}]" if filter_main else ""),
            border_style="#ff8c00",
            header_style="bold white",
            show_lines=False,
        )
        table.add_column("Имя", style="white", no_wrap=True)
        table.add_column("Мейн", style="#ff8c00")
        table.add_column("Роль", style="dim white")
        table.add_column("Модель", style="dim white")
        table.add_column("Тики", justify="right", style="dim")
        table.add_column("Статус", style="green")
        table.add_column("Сессия", style="dim")

        for s in active_subs:
            status = s.get("status", "active")
            status_color = "green" if status == "active" else "dim red" if status == "done" else "yellow"
            table.add_row(
                s.get("name", "—"),
                s.get("main", "—"),
                s.get("role", "—")[:30],
                s.get("model", "—")[:25],
                str(s.get("ticks", 0)),
                Text(status, style=status_color),
                s.get("session", "—"),
            )

        console.print(table)
        console.print(f"  [dim]Всего: {len(active_subs)} суб-агентов[/dim]")

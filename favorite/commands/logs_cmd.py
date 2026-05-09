"""
favorite/commands/logs_cmd.py — /logs command.
View session logs and system events.
"""
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from .base import ICommand, CommandContext

console = Console()


def _load_session_history(workdir: str, session_id: str) -> list[dict]:
    path = Path(workdir) / "sessions" / session_id / "history.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _format_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ts[:8] if ts else ""


class LogsCommand(ICommand):
    name = "/logs"
    description = "Просмотр системных событий и истории сессии"
    priority = 55

    def execute(self, args: str, ctx: CommandContext) -> None:
        arg = args.strip().lower()
        sessions_root = Path(ctx.workdir) / "sessions"

        if arg == "all":
            # List all sessions
            if not sessions_root.exists():
                console.print("  [dim]Сессий нет[/dim]")
                return
            dirs = sorted(sessions_root.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)[:20]
            console.print()
            console.print("  [bold #ff8c00]Последние сессии:[/bold #ff8c00]")
            for d in dirs:
                meta_f = d / "meta.json"
                if meta_f.exists():
                    try:
                        meta = json.loads(meta_f.read_text(encoding="utf-8"))
                        title = meta.get("title", d.name)[:40]
                        created = meta.get("created_at", "")[:16]
                        console.print(f"  [dim]{escape(created)}[/dim]  [bold]{escape(d.name[:8])}[/bold]  {escape(title)}")
                    except Exception:
                        console.print(f"  [dim]{d.name}[/dim]")
            console.print()
            return

        # Show current session events log
        console.print()
        console.print(f"  [bold #ff8c00]События сессии: {escape(ctx.session_id[:12])}[/bold #ff8c00]")
        console.print()

        events_file = Path(ctx.workdir) / "sessions" / ctx.session_id / "events.json"
        if events_file.exists():
            try:
                events = json.loads(events_file.read_text(encoding="utf-8"))
                if events:
                    for ev in events[-30:]:
                        ts = _format_ts(ev.get("ts", ""))
                        kind = ev.get("kind", "event")
                        msg = ev.get("msg", "")[:100]
                        console.print(f"  [dim #666666]{ts}[/dim #666666]  [bold #ff8c00]{escape(kind)}[/bold #ff8c00]  {escape(msg)}")
                    console.print()
                    console.print(f"  [dim]Всего событий: {len(events)}[/dim]")
                else:
                    console.print("  [dim]Событий нет[/dim]")
            except Exception as e:
                console.print(f"  [red]{escape(str(e))}[/red]")
        else:
            # Fallback: show history entries
            history = _load_session_history(ctx.workdir, ctx.session_id)
            if not history:
                console.print("  [dim]История сессии пуста[/dim]")
            else:
                for entry in history[-20:]:
                    role = entry.get("type", entry.get("role", "?"))
                    content = (entry.get("content") or "")[:80]
                    ts = _format_ts(entry.get("ts", ""))
                    color = "#ff8c00" if role in ("user",) else "#888888"
                    console.print(f"  [dim #666666]{ts}[/dim #666666] [{color}]{escape(role)}[/{color}]: {escape(content)}")
        console.print()


def log_event(workdir: str, session_id: str, kind: str, msg: str) -> None:
    """Write a system event to events.json for the current session."""
    try:
        events_file = Path(workdir) / "sessions" / session_id / "events.json"
        events_file.parent.mkdir(parents=True, exist_ok=True)
        events = []
        if events_file.exists():
            events = json.loads(events_file.read_text(encoding="utf-8"))
        events.append({"ts": datetime.now().isoformat(), "kind": kind, "msg": msg})
        events_file.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

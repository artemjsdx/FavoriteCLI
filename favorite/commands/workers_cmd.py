"""
favorite/commands/workers_cmd.py — /workers command (§43).
Manage long-running background worker processes.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from .base import ICommand, CommandContext

console = Console()
_WORKERS_DIR = Path.home() / ".favorite" / "workers"
_WORKERS_JSON = _WORKERS_DIR / "workers.json"


def _load_workers() -> list[dict]:
    if _WORKERS_JSON.exists():
        try:
            return json.loads(_WORKERS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_workers(workers: list[dict]) -> None:
    _WORKERS_DIR.mkdir(parents=True, exist_ok=True)
    _WORKERS_JSON.write_text(json.dumps(workers, indent=2, ensure_ascii=False), encoding="utf-8")


def _is_tmux_alive(session_name: str) -> bool:
    try:
        r = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def _check_worker_status(w: dict) -> str:
    if w.get("status") == "stopped":
        return "stopped"
    tmux = w.get("tmux_session", "")
    if tmux and _is_tmux_alive(tmux):
        return "running"
    return "crashed"


def check_workers_on_startup() -> list[dict]:
    """Check all workers on CLI startup. Returns list of crashed workers."""
    workers = _load_workers()
    crashed = []
    changed = False
    for w in workers:
        if w.get("status") == "running":
            real_status = _check_worker_status(w)
            if real_status == "crashed":
                w["status"] = "crashed"
                w["crashed_at"] = datetime.utcnow().isoformat()
                crashed.append(w)
                changed = True
    if changed:
        _save_workers(workers)
    return crashed


class WorkersCommand(ICommand):
    name = "/workers"
    description = "Управление фоновыми воркерами"
    priority = 80

    def execute(self, args: str, ctx: CommandContext) -> None:
        args = (args or "").strip().lower()
        workers = _load_workers()

        if args in ("", "list"):
            self._show_list(workers)
        elif args == "check":
            crashed = check_workers_on_startup()
            if crashed:
                console.print(f"  [red]Упавших воркеров: {len(crashed)}[/red]")
                for w in crashed:
                    console.print(f"  [dim]  {w['id']}: {escape(w.get('name','?'))}[/dim]")
            else:
                console.print("  [dim #666666]Все воркеры работают нормально[/dim #666666]")
        elif args.startswith("stop "):
            wid = args[5:].strip()
            self._stop_worker(wid, workers)
        elif args.startswith("logs "):
            wid = args[5:].strip()
            self._show_logs(wid, workers)
        else:
            console.print("  [dim]Команды: /workers | /workers list | /workers check | /workers stop <id> | /workers logs <id>[/dim]")

    def _show_list(self, workers: list[dict]) -> None:
        if not workers:
            console.print("  [dim #666666]Воркеров нет. Агент может создать воркера по запросу.[/dim #666666]")
            return
        table = Table(show_header=True, header_style="bold #ff8c00", box=None)
        table.add_column("ID", style="dim", width=8)
        table.add_column("Имя")
        table.add_column("Статус", width=10)
        table.add_column("Запущен", width=20)
        for w in workers:
            real_status = _check_worker_status(w)
            status_style = {"running": "green", "crashed": "red", "stopped": "dim"}.get(real_status, "dim")
            status_icon = {"running": "▶", "crashed": "✗", "stopped": "■"}.get(real_status, "?")
            table.add_row(
                w.get("id", "?"),
                escape(w.get("name", "?")),
                f"[{status_style}]{status_icon} {real_status}[/{status_style}]",
                (w.get("started_at", "?")[:16].replace("T", " ")),
            )
        console.print(table)

    def _stop_worker(self, worker_id: str, workers: list[dict]) -> None:
        w = next((w for w in workers if w.get("id") == worker_id), None)
        if not w:
            console.print(f"  [red]Воркер '{worker_id}' не найден[/red]")
            return
        tmux = w.get("tmux_session", "")
        if tmux:
            try:
                subprocess.run(["tmux", "kill-session", "-t", tmux], timeout=5)
                console.print(f"  [dim]Воркер {worker_id} остановлен[/dim]")
            except Exception as e:
                console.print(f"  [red]Ошибка остановки: {e}[/red]")
        w["status"] = "stopped"
        _save_workers(workers)

    def _show_logs(self, worker_id: str, workers: list[dict]) -> None:
        w = next((w for w in workers if w.get("id") == worker_id), None)
        if not w:
            console.print(f"  [red]Воркер '{worker_id}' не найден[/red]")
            return
        log_path = Path.home() / ".favorite" / "workers" / worker_id / "worker.log"
        if not log_path.exists():
            console.print(f"  [dim]Лог не найден: {log_path}[/dim]")
            return
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
            for line in lines:
                console.print(f"  [dim]{escape(line)}[/dim]")
        except Exception as e:
            console.print(f"  [red]Ошибка чтения лога: {e}[/red]")

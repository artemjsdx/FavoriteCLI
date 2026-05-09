"""
favorite/commands/sandbox_cmd.py — §19.6 /sandbox command.
Manage sub-agent sandbox isolation settings.
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

console = Console()
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_MODULES_FILE = _CONFIG_DIR / "modules.json"


def _load_modules() -> dict:
    if _MODULES_FILE.exists():
        try:
            return json.loads(_MODULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_modules(d: dict) -> None:
    _MODULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MODULES_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_sandbox(args: list[str], ctx, cfg) -> None:
    """
    /sandbox [on|off|review on|off|status|clean|paths]

    Manage sub-agent sandbox isolation.
    """
    sub = args[0].lower() if args else ""

    if sub in ("on", "вкл"):
        _toggle_sandbox(True)
    elif sub in ("off", "выкл"):
        _toggle_sandbox(False)
    elif sub == "review":
        val = args[1].lower() if len(args) > 1 else ""
        _toggle_review(val not in ("off", "выкл", "0", "false"))
    elif sub in ("clean", "очистить"):
        _clean_workspaces(ctx)
    elif sub in ("paths", "пути"):
        _show_paths(ctx)
    else:
        _show_status(ctx)


def _toggle_sandbox(enable: bool) -> None:
    m = _load_modules()
    m["sub_sandbox"] = enable
    _save_modules(m)
    state = "[green]ON[/green]" if enable else "[dim]OFF[/dim]"
    console.print(f"  ✓ sub_sandbox → {state}")
    if enable:
        console.print("  [dim]Субы будут работать в изолированных копиях рабочей папки.[/dim]")
        console.print("  [dim]Изменения применяются только после SUB_DELIVER + APPROVE_SUB.[/dim]")


def _toggle_review(enable: bool) -> None:
    m = _load_modules()
    m["sub_change_review"] = enable
    _save_modules(m)
    state = "[green]ON[/green]" if enable else "[dim]OFF[/dim]"
    console.print(f"  ✓ sub_change_review → {state}")


def _show_status(ctx) -> None:
    m = _load_modules()
    sandbox = m.get("sub_sandbox", False)
    review  = m.get("sub_change_review", True)

    sub_ws = Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    pending = list(sub_ws.glob("pending_*.json")) if sub_ws.exists() else []
    applied = list(sub_ws.glob("applied_*.json")) if sub_ws.exists() else []

    table = Table(box=None, padding=(0, 2), show_header=False)
    table.add_column("K", style="dim", width=24)
    table.add_column("V")
    table.add_row("sub_sandbox",      "[green]ON[/green]" if sandbox else "[dim]OFF[/dim]")
    table.add_row("sub_change_review","[green]ON[/green]" if review else "[dim]OFF[/dim]")
    table.add_row("Ожидают ревью",    str(len(pending)))
    table.add_row("Применено",        str(len(applied)))
    table.add_row("Рабочая папка",    str(sub_ws))

    console.print()
    console.print(Panel(
        table,
        title="[bold #ff8c00]⬡  Суб-сандбокс[/bold #ff8c00]",
        subtitle="[dim]/sandbox on|off  /sandbox review on|off  /sandbox clean[/dim]",
        border_style="#ff8c00",
    ))

    if pending:
        console.print(f"  [bold]Ожидают проверки:[/bold]")
        for p in pending[:5]:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                console.print(f"    [cyan]{d.get('diff_id','?')}[/cyan] от {d.get('from','?')} — {d.get('ts','')[:16]}")
            except Exception:
                console.print(f"    {p.name}")


def _clean_workspaces(ctx) -> None:
    import shutil
    sub_ws = Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    if not sub_ws.exists():
        console.print("  [dim]sub_workspaces пусто.[/dim]")
        return
    removed = 0
    for p in sub_ws.glob("discarded_*.json"):
        p.unlink(); removed += 1
    for p in sub_ws.glob("applied_*.json"):
        p.unlink(); removed += 1
    console.print(f"  ✓ Очищено {removed} файлов истории.")


def _show_paths(ctx) -> None:
    sub_ws = Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    console.print(f"  Sub workspaces: {sub_ws}")
    if sub_ws.exists():
        for p in sorted(sub_ws.iterdir())[:20]:
            console.print(f"    {p.name}")


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class SandboxCommand(ICommand):
    name = "/sandbox"
    description = "Суб-агент сандбокс — изоляция изменений"
    priority = 65

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_sandbox(arg_list, ctx, getattr(ctx, "config", None))

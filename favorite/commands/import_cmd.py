"""
favorite/commands/import_cmd.py — §13 /import memory command.
Restores a tar.gz archive created by /export memory.
Handles conflicts with user confirmation.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

console = Console()


def cmd_import(args: list[str], ctx, cfg) -> None:
    """
    /import memory <path>

    Restores memory from a tar.gz archive (created by /export memory).
    Detects conflicts, asks what to overwrite.
    """
    sub      = args[0].lower() if args else ""
    src_path = args[1] if len(args) > 1 else (args[0] if args and "." in args[0] else "")

    if sub not in ("memory", "мемори", "mem", "all") and not src_path:
        console.print("  [dim]Использование: /import memory <путь_к_архиву>[/dim]")
        return

    if sub in ("memory", "мемори", "mem", "all"):
        arc_path = Path(src_path) if src_path else None
    else:
        arc_path = Path(sub)

    if not arc_path:
        console.print("  [red]Укажи путь к архиву:[/red] /import memory /path/to/favorite_memory.tar.gz")
        return

    arc_path = arc_path.expanduser().resolve()
    if not arc_path.exists():
        console.print(f"  [red]Архив не найден:[/red] {escape(str(arc_path))}")
        return

    base = Path(ctx.workdir)

    console.print()
    console.print(f"  [bold #ff8c00]📥 Импорт памяти из {escape(str(arc_path))}[/bold #ff8c00]")

    try:
        with tarfile.open(str(arc_path), "r:gz") as tar:
            members = tar.getmembers()

            # Read manifest
            manifest_m = next((m for m in members if m.name == "manifest.json"), None)
            manifest = {}
            if manifest_m:
                f = tar.extractfile(manifest_m)
                if f:
                    manifest = json.loads(f.read().decode("utf-8"))

            console.print(f"  Файлов в архиве: [cyan]{len(members)}[/cyan]")
            if manifest.get("created_at"):
                console.print(f"  Создан: [dim]{manifest['created_at'][:16]}[/dim]")

            # Detect conflicts
            conflicts: list[str] = []
            checksum_fails: list[str] = []
            for m in members:
                if m.name == "manifest.json":
                    continue
                dst = base / m.name
                if dst.exists():
                    conflicts.append(m.name)

            if conflicts:
                console.print()
                console.print(f"  [yellow]⚠ Конфликты ({len(conflicts)} файлов):[/yellow]")
                for c in conflicts[:10]:
                    console.print(f"    [dim]{c}[/dim]")
                if len(conflicts) > 10:
                    console.print(f"    [dim]...и ещё {len(conflicts)-10}[/dim]")
                console.print()
                console.print("  [bold]Перезаписать всё? [dim](yes/no/selective)[/dim][/bold]")
                try:
                    ans = input("  → ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    console.print("  Отменено.")
                    return

                if ans in ("no", "n", "нет"):
                    console.print("  [dim]Импорт отменён.[/dim]")
                    return
                elif ans == "selective":
                    skip_set = _selective_skip(conflicts)
                else:
                    skip_set = set()
            else:
                skip_set = set()

            # Extract
            extracted = 0
            skipped   = 0
            for m in members:
                if m.name == "manifest.json":
                    continue
                if m.name in skip_set:
                    skipped += 1
                    continue
                dst = base / m.name
                if m.isfile():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    src_f = tar.extractfile(m)
                    if src_f:
                        dst.write_bytes(src_f.read())
                        extracted += 1

            console.print()
            console.print(Panel(
                f"  Восстановлено: [green]{extracted}[/green] файлов\n"
                f"  Пропущено:     [dim]{skipped}[/dim] файлов\n"
                f"  Из архива:     [dim]{escape(str(arc_path))}[/dim]",
                title="[bold #ff8c00]✅ Импорт завершён[/bold #ff8c00]",
                border_style="#ff8c00",
            ))

    except Exception as e:
        console.print(f"  [red]Ошибка импорта: {escape(str(e))}[/red]")


def _selective_skip(conflicts: list[str]) -> set:
    """Ask user which files to skip."""
    skip_set = set()
    console.print()
    console.print("  [dim]Введи номера файлов которые ПРОПУСТИТЬ (через пробел), или Enter для всех:[/dim]")
    for i, c in enumerate(conflicts, 1):
        console.print(f"    {i}. {c}")
    try:
        raw = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        return skip_set
    for tok in raw.split():
        if tok.isdigit():
            idx = int(tok) - 1
            if 0 <= idx < len(conflicts):
                skip_set.add(conflicts[idx])
    return skip_set


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class ImportCommand(ICommand):
    name = "/import"
    description = "Импорт памяти/сессии из архива с разрешением конфликтов"
    priority = 51

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_import(arg_list, ctx, getattr(ctx, "config", None))

"""
favorite/commands/export_cmd.py — §13 /export memory command.
Creates a tar.gz archive with all memory, sessions, config, agents.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import track

console = Console()
_MSK = timezone(timedelta(hours=3))


def cmd_export(args: list[str], ctx, cfg) -> None:
    """
    /export memory [output_path]

    Creates a tar.gz archive containing:
    - config/ (api_keys, modules, user_agents, user_prompt, mode)
    - sessions/<id>/  (memory, tasks, plan, auto.log)
    - agents/ (.md characters)
    - favorite/agent/sub_roles_library.json
    - manifest.json (checksums, metadata)
    """
    sub = args[0].lower() if args else "memory"

    if sub not in ("memory", "мемори", "mem", "all"):
        console.print(f"  [dim]Использование: /export memory [путь][/dim]")
        return

    ts   = datetime.now(_MSK).strftime("%Y%m%d_%H%M")
    name = f"favorite_memory_{ts}.tar.gz"
    out_path = Path(args[1]) if len(args) > 1 else Path(ctx.workdir) / name

    console.print()
    console.print(f"  [bold #ff8c00]📦 Экспорт памяти → {escape(str(out_path))}[/bold #ff8c00]")

    base = Path(ctx.workdir)
    files_to_pack: list[tuple[Path, str]] = []   # (abs_path, archive_name)
    checksums: dict[str, str] = {}

    # ── Collect files ────────────────────────────────────────────────────────
    INCLUDE_DIRS = [
        (base / "config",   "config"),
        (base / "agents",   "agents"),
    ]
    INCLUDE_FILES = [
        base / "favorite" / "agent" / "sub_roles_library.json",
        base / "Favorite.md",
    ]

    for src_dir, arc_base in INCLUDE_DIRS:
        if src_dir.exists():
            for f in sorted(src_dir.rglob("*")):
                if f.is_file() and not _is_secret(f):
                    rel = arc_base + "/" + str(f.relative_to(src_dir))
                    files_to_pack.append((f, rel))

    for f in INCLUDE_FILES:
        if f.exists():
            files_to_pack.append((f, f.name))

    # Current session memory
    sess_dir = base / "sessions" / ctx.session_id
    if sess_dir.exists():
        for f in sorted(sess_dir.rglob("*")):
            if f.is_file():
                rel = "session/" + str(f.relative_to(sess_dir))
                files_to_pack.append((f, rel))

    # ── Checksums ────────────────────────────────────────────────────────────
    for f, arc_name in files_to_pack:
        try:
            data = f.read_bytes()
            checksums[arc_name] = hashlib.sha256(data).hexdigest()
        except Exception:
            checksums[arc_name] = "error"

    manifest = {
        "version":     2,
        "created_at":  datetime.now(_MSK).isoformat(),
        "session_id":  ctx.session_id,
        "workdir":     str(base),
        "file_count":  len(files_to_pack),
        "checksums":   checksums,
    }

    # ── Write archive ────────────────────────────────────────────────────────
    try:
        with tarfile.open(str(out_path), "w:gz", compresslevel=6) as tar:
            for f, arc_name in track(files_to_pack, description="Упаковываю...", console=console):
                tar.add(str(f), arcname=arc_name)
            # Add manifest
            import io as _io
            mdata = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
            minfo = tarfile.TarInfo(name="manifest.json")
            minfo.size = len(mdata)
            tar.addfile(minfo, _io.BytesIO(mdata))

        size_kb = out_path.stat().st_size // 1024
        console.print()
        console.print(Panel(
            f"  Файлов: [cyan]{len(files_to_pack)}[/cyan]\n"
            f"  Размер: [cyan]{size_kb} KB[/cyan]\n"
            f"  Путь:   [cyan]{escape(str(out_path))}[/cyan]",
            title="[bold #ff8c00]✅ Экспорт завершён[/bold #ff8c00]",
            border_style="#ff8c00",
        ))
    except Exception as e:
        console.print(f"  [red]Ошибка экспорта: {escape(str(e))}[/red]")


def _is_secret(f: Path) -> bool:
    sensitive = ("api_keys.json", ".env", "secrets")
    return any(s in f.name for s in sensitive)


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class ExportCommand(ICommand):
    name = "/export"
    description = "Экспорт памяти/сессии в tar.gz архив"
    priority = 50

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_export(arg_list, ctx, getattr(ctx, "config", None))

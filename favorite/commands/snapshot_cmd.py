"""
favorite/commands/snapshot_cmd.py — /snapshot and /rollback commands.
"""
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()
_SNAP_DIR_NAME = ".fav_snapshots"


def _snapshots_dir(workdir: str) -> Path:
    d = Path(workdir) / _SNAP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _list_snapshots(workdir: str) -> list[dict]:
    sd = _snapshots_dir(workdir)
    meta_file = sd / "index.json"
    if not meta_file.exists():
        return []
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_index(workdir: str, snaps: list[dict]) -> None:
    sd = _snapshots_dir(workdir)
    (sd / "index.json").write_text(json.dumps(snaps, ensure_ascii=False, indent=2), encoding="utf-8")


def create_snapshot(workdir: str, note: str = "") -> dict:
    snap_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_meta = {"id": snap_id, "note": note or snap_id, "ts": datetime.now().isoformat()}
    try:
        r = subprocess.run(
            ["git", "stash", "push", "-u", "-m", f"fav_snap_{snap_id}"],
            cwd=workdir, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0 and "No local changes" not in r.stdout:
            snap_meta["method"] = "git_stash"
            snap_meta["stash_ref"] = "stash@{0}"
    except Exception:
        pass
    if "method" not in snap_meta:
        sd = _snapshots_dir(workdir)
        dest = sd / snap_id
        try:
            shutil.copytree(workdir, str(dest), ignore=shutil.ignore_patterns(
                _SNAP_DIR_NAME, ".git", "__pycache__", "*.pyc", "sessions"
            ))
            snap_meta["method"] = "copy"
        except Exception as e:
            snap_meta["method"] = "failed"
            snap_meta["error"] = str(e)
    snaps = _list_snapshots(workdir)
    snaps.insert(0, snap_meta)
    snaps = snaps[:20]
    _save_index(workdir, snaps)
    return snap_meta


class SnapshotCommand(ICommand):
    name = "/snapshot"
    description = "Сохранить снапшот текущего состояния проекта"
    priority = 60

    def execute(self, args: str, ctx: CommandContext) -> None:
        note = args.strip() or ""
        console.print()
        console.print("  [bold #ff8c00]📸  Создаю снапшот...[/bold #ff8c00]")
        snap = create_snapshot(ctx.workdir, note)
        if snap.get("method") == "failed":
            console.print(f"  [red]Ошибка: {escape(snap.get('error',''))}[/red]")
        else:
            method = "git stash" if snap.get("method") == "git_stash" else "копия файлов"
            console.print(f"  [dim #666666]✓ Снапшот {escape(snap['id'])} ({method})[/dim #666666]")
            if note:
                console.print(f"  [dim]Заметка: {escape(note)}[/dim]")
        console.print()


class RollbackCommand(ICommand):
    name = "/rollback"
    description = "Откатиться к снапшоту (последнему или выбранному)"
    priority = 61

    def execute(self, args: str, ctx: CommandContext) -> None:
        snaps = _list_snapshots(ctx.workdir)
        if not snaps:
            console.print()
            console.print("  [dim]Снапшотов нет. Используй /snapshot чтобы создать.[/dim]")
            console.print()
            return

        target_id = args.strip()
        if not target_id:
            console.print()
            console.print("  [bold #ff8c00]Доступные снапшоты:[/bold #ff8c00]")
            for i, s in enumerate(snaps[:10], 1):
                ts = s.get("ts", "")[:16]
                note = s.get("note", s.get("id", ""))
                method = "📦 git" if s.get("method") == "git_stash" else "📁 copy"
                console.print(f"  {i}. {escape(ts)}  {method}  {escape(note)}")
            console.print()
            try:
                choice = input("  Введи номер (или Enter для отмены): ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not choice:
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(snaps):
                    target_id = snaps[idx]["id"]
                else:
                    console.print("  [red]Неверный номер[/red]")
                    return
            except ValueError:
                target_id = choice

        snap = next((s for s in snaps if s["id"] == target_id), None)
        if not snap:
            console.print(f"  [red]Снапшот не найден: {escape(target_id)}[/red]")
            return

        console.print()
        console.print(f"  [bold #ff8c00]↩  Откат к {escape(snap['id'])}...[/bold #ff8c00]")
        if snap.get("method") == "git_stash":
            try:
                r = subprocess.run(["git", "stash", "list"], cwd=ctx.workdir, capture_output=True, text=True, timeout=10)
                stash_idx = None
                for line in r.stdout.splitlines():
                    if f"fav_snap_{snap['id']}" in line:
                        stash_idx = line.split(":")[0]
                        break
                if stash_idx:
                    r2 = subprocess.run(["git", "stash", "pop", stash_idx], cwd=ctx.workdir, capture_output=True, text=True, timeout=15)
                    if r2.returncode == 0:
                        console.print("  [dim #666666]✓ Откат выполнен (git stash pop)[/dim #666666]")
                    else:
                        console.print(f"  [red]{escape(r2.stderr[:200])}[/red]")
                else:
                    console.print("  [red]Stash не найден в git[/red]")
            except Exception as e:
                console.print(f"  [red]{escape(str(e))}[/red]")
        elif snap.get("method") == "copy":
            sd = _snapshots_dir(ctx.workdir)
            src = sd / snap["id"]
            if src.exists():
                try:
                    for item in src.iterdir():
                        dst = Path(ctx.workdir) / item.name
                        if item.is_dir():
                            if dst.exists():
                                shutil.rmtree(dst)
                            shutil.copytree(str(item), str(dst))
                        else:
                            shutil.copy2(str(item), str(dst))
                    console.print("  [dim #666666]✓ Откат выполнен[/dim #666666]")
                except Exception as e:
                    console.print(f"  [red]{escape(str(e))}[/red]")
            else:
                console.print("  [red]Папка снапшота не найдена[/red]")
        console.print()

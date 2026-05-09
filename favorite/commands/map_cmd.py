"""
favorite/commands/map_cmd.py — /map command.
Renders a Rich tree view of the working directory.
"""
from pathlib import Path
from rich.console import Console
from rich.tree import Tree
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()

_SKIP = {
  ".git", "__pycache__", "node_modules", ".venv", "venv",
  ".mypy_cache", ".pytest_cache", "dist", "build", ".tox", ".eggs",
}


class MapCommand(ICommand):
  name = "/map"
  description = "Карта файлов рабочей директории"
  priority = 13

  def execute(self, args: str, ctx: CommandContext) -> None:
      base = Path(ctx.workdir)
      subpath = args.strip()
      if subpath:
          candidate = base / subpath
          if candidate.exists():
              base = candidate
          else:
              console.print(f"  [red]Путь не найден: {candidate}[/red]")
              return

      tree = Tree(f"[bold #ff8c00]{escape(str(base))}[/bold #ff8c00]")
      file_count, total_size = self._build_tree(base, tree, depth=0)
      console.print(tree)
      size_kb = total_size / 1024
      console.print(f"  [dim]Файлов: {file_count} · Размер: {size_kb:.1f} КБ[/dim]")

  def _build_tree(self, path: Path, node, depth: int) -> tuple:
      if depth > 4:
          node.add("[dim #888888]... (глубже не показываем)[/dim #888888]")
          return 0, 0
      file_count = 0
      total_size = 0
      try:
          entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
      except PermissionError:
          node.add("[dim red]<нет доступа>[/dim red]")
          return 0, 0
      for entry in entries:
          if entry.name in _SKIP or entry.name.startswith("."):
              continue
          if entry.is_dir():
              branch = node.add(f"[bold]{escape(entry.name)}/[/bold]")
              fc, ts = self._build_tree(entry, branch, depth + 1)
              file_count += fc
              total_size += ts
          else:
              try:
                  size = entry.stat().st_size
              except OSError:
                  size = 0
              total_size += size
              file_count += 1
              sz = f"{size/1024:.1f}к" if size >= 1024 else f"{size}б"
              node.add(f"[dim]{escape(entry.name)}[/dim] [dim #888888]{sz}[/dim #888888]")
      return file_count, total_size

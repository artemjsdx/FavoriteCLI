"""
favorite/commands/silent_cmd.py — /silent toggle
"""
from .base import ICommand, CommandContext
from rich.console import Console
from rich.markup import escape

console = Console()
_SILENT = False


def is_silent() -> bool:
  return _SILENT


class SilentCommand(ICommand):
  name = "/silent"
  description = "Включить/выключить тихий режим (скрыть STEP и shell-вывод)"
  priority = 20

  def execute(self, args: str, ctx: CommandContext) -> None:
      global _SILENT
      arg = args.strip().lower()
      if arg in ("on", "1", "yes"): _SILENT = True
      elif arg in ("off", "0", "no"): _SILENT = False
      else: _SILENT = not _SILENT
      state = "[bold #ff8c00]ВКЛ[/bold #ff8c00]" if _SILENT else "[dim]ВЫКЛ[/dim]"
      console.print(f"\n  ● Тихий режим: {state}")
      if _SILENT:
          console.print("  [dim]Теги STEP, shell-вывод и статусы агента скрыты.[/dim]")
      console.print()

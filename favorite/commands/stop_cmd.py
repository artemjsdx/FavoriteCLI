"""
favorite/commands/stop_cmd.py — /stop command.
Signals the current agent run loop to stop gracefully.
"""
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()


class StopCommand(ICommand):
    name = "/stop"
    description = "Остановить текущую задачу агента"
    priority = 8

    def execute(self, args: str, ctx: CommandContext) -> None:
        if ctx.auto_mode:
            ctx.auto_mode = False
            console.print()
            console.print("  [bold #ff8c00]⏹  Авто-режим остановлен[/bold #ff8c00]")
            console.print("  [dim]Агент завершит текущий такт и остановится.[/dim]")
        elif hasattr(ctx, "plan_mode") and ctx.plan_mode:
            ctx.plan_mode = False  # type: ignore
            console.print()
            console.print("  [bold #ff8c00]⏹  Режим /plan остановлен[/bold #ff8c00]")
        else:
            console.print()
            console.print("  [dim]Нет активного режима для остановки.[/dim]")
            console.print("  [dim]Подсказка: Ctrl+C завершает текущую генерацию.[/dim]")
        console.print()

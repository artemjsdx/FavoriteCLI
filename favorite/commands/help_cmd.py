"""
favorite/commands/help_cmd.py — /help command.
"""
from rich.console import Console
from rich.table import Table
from .base import ICommand, CommandContext

console = Console()


class HelpCommand(ICommand):
    name = "/help"
    description = "Список всех команд"
    priority = 5

    def execute(self, args: str, ctx: CommandContext) -> None:
        reg = ctx.registry
        if not reg:
            console.print("[dim]Реестр команд недоступен[/dim]")
            return
        table = Table(show_header=True, header_style="bold #ff8c00", box=None, padding=(0, 2))
        table.add_column("Команда", style="bold #ff8c00", no_wrap=True)
        table.add_column("Описание", style="dim #cccccc")
        for cmd in reg.all_sorted():
            table.add_row(cmd.name, cmd.description)
        console.print()
        console.print("  [bold #ff8c00]Доступные команды:[/bold #ff8c00]")
        console.print()
        console.print(table)
        console.print()
        console.print("  [dim]Введи сообщение без / чтобы написать агенту.[/dim]")
        console.print()

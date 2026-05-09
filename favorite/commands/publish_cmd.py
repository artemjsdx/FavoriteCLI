"""
favorite/commands/publish_cmd.py — /publish command.
Commits and pushes current workdir to GitHub.
"""
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()


class PublishCommand(ICommand):
    name = "/publish"
    description = "Запушить изменения на GitHub (git commit + push)"
    priority = 45

    def execute(self, args: str, ctx: CommandContext) -> None:
        cfg = ctx.config
        msg = args.strip() or "auto: agent publish"
        console.print()
        console.print(f"  [bold #ff8c00]↑  Публикация изменений[/bold #ff8c00]")
        console.print(f"  [dim]Сообщение коммита: {escape(msg)}[/dim]")
        console.print()
        try:
            from ..github.auto_push import AutoPush
            AutoPush(cfg).push_workdir(ctx.workdir, commit_msg=msg)
            console.print("  [dim #666666]✓ Push выполнен[/dim #666666]")
        except Exception as e:
            console.print(f"  [red]Ошибка push: {escape(str(e))}[/red]")
        console.print()

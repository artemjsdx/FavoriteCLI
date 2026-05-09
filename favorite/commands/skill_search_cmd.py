"""
favorite/commands/skill_search_cmd.py — /skill-search command.
Search and view available skills.
"""
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from .base import ICommand, CommandContext

console = Console()


class SkillSearchCommand(ICommand):
    name = "/skill-search"
    description = "Поиск и просмотр доступных скиллов"
    priority = 48

    def execute(self, args: str, ctx: CommandContext) -> None:
        from ..skills.registry import SkillRegistry
        SkillRegistry.load_config()
        query = args.strip().lower()
        all_skills = SkillRegistry.all_skills()

        if query:
            all_skills = [s for s in all_skills if query in s.name.lower() or query in s.get_prompt_snippet().lower()]

        if not all_skills:
            console.print()
            console.print("  [dim]Скиллов не найдено[/dim]")
            console.print()
            return

        console.print()
        console.print(f"  [bold #ff8c00]Скиллы{'  (поиск: ' + escape(query) + ')' if query else ''}:[/bold #ff8c00]")
        console.print()

        table = Table(show_header=True, header_style="bold #ff8c00", box=None, padding=(0, 2))
        table.add_column("Скилл", style="bold #cccccc", no_wrap=True)
        table.add_column("Статус", style="dim #888888")
        table.add_column("Описание", style="dim #cccccc")

        for skill in all_skills:
            status = "[bold #4CAF50]вкл[/bold #4CAF50]" if skill.enabled else "[dim #555555]выкл[/dim #555555]"
            snippet = skill.get_prompt_snippet()
            # Take first non-empty line after the header
            lines = [l.strip() for l in snippet.splitlines() if l.strip() and not l.startswith('#')]
            desc = lines[0][:60] if lines else ""
            table.add_row(escape(skill.name), status, escape(desc))

        console.print(table)
        console.print()
        console.print("  [dim]Управление скиллами: /skills[/dim]")
        console.print()

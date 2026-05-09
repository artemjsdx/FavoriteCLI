"""
favorite/commands/userprompt_cmd.py — /userprompt command.
"""
import json
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()
_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "user_prompt.json"


def load_user_prompt() -> str:
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            return data.get("template", "")
        except Exception:
            pass
    return ""


def save_user_prompt(template: str) -> None:
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps({"template": template}, ensure_ascii=False, indent=2), encoding="utf-8")


class UserPromptCommand(ICommand):
    name = "/userprompt"
    description = "Задать шаблон промпта (приписывается к каждому сообщению)"
    priority = 52

    def execute(self, args: str, ctx: CommandContext) -> None:
        arg = args.strip()
        current = load_user_prompt()

        if arg == "clear":
            save_user_prompt("")
            console.print("  [dim #666666]Пользовательский промпт очищен[/dim #666666]")
            return

        if arg in ("show", ""):
            console.print()
            console.print("  [bold #ff8c00]Пользовательский промпт:[/bold #ff8c00]")
            console.print()
            if current:
                console.print(f"  {escape(current)}")
            else:
                console.print("  [dim](пусто — промпт не задан)[/dim]")
            console.print()
            console.print("  [dim]Установить: /userprompt <текст>[/dim]")
            console.print("  [dim]Очистить:   /userprompt clear[/dim]")
            console.print()
            return

        save_user_prompt(arg)
        console.print()
        console.print(f"  [bold #ff8c00]✓ Промпт установлен[/bold #ff8c00]")
        console.print(f"  [dim]{escape(arg[:120])}[/dim]")
        console.print()

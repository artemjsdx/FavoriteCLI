import os
import subprocess
from rich.panel import Panel
from rich.console import Console
from .base import ICommand
from ..memory.favorite_md import FavoriteMd

console = Console()

class MemoryCommand(ICommand):
  name = "/memory"
  description = "Показать или редактировать Favorite.md (память агента)"

  def execute(self, args: str, ctx) -> None:
    fav_md = FavoriteMd()
        
    if args.strip().lower() == "edit":
        editor = os.environ.get("EDITOR")
        path = fav_md._path
        if editor:
            try:
                subprocess.run([editor, str(path)])
                return
            except Exception as e:
                console.print(f"[red]Ошибка при запуске редактора: {e}[/red]")
            
        console.print(f"\n  [bold #ff8c00]Отредактируй файл:[/bold #ff8c00] [underline]{path}[/underline]\n")
        return
  
    # Default: show content
    content = fav_md.read()
    if not content:
        console.print("[dim]Favorite.md пуст или не существует.[/dim]")
        return
  
    panel = Panel(
        content,
        title="[bold #ff8c00]Favorite.md[/bold #ff8c00]",
        border_style="#ff8c00",
        padding=(1, 2)
    )
    console.print(panel)
    console.print("[dim]Используй [/dim][bold]/memory edit[/bold][dim] для редактирования.[/dim]\n")
  
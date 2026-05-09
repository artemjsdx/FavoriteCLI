from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timezone
import os
from .base import ICommand, CommandContext
from ..memory.favorite_md import _DEFAULT as FAV_MD_PATH

console = Console()

class UsageCommand(ICommand):
  name = "/usage"
  description = "Показать статистику использования сессии"
  priority = 10

  def execute(self, args: str, ctx: CommandContext) -> None:
    from ..sessions.manager import SessionManager
    mgr = SessionManager()
    meta = mgr.get_session(ctx.session_id)
        
    if not meta:
        console.print("[red]Сессия не найдена.[/red]")
        return
  
    stats = meta.get("stats", {
        "total_tokens": 0,
        "requests": 0,
        "start_time": meta.get("created_at")
    })
  
    # Duration
    start_dt = datetime.fromisoformat(stats["start_time"])
    now = datetime.now(timezone.utc)
    duration = now - start_dt
        
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = f"{hours}ч {minutes}м {seconds}с"
  
    # Favorite.md size
    fav_size = 0
    if FAV_MD_PATH.exists():
        fav_size = len(FAV_MD_PATH.read_text(encoding="utf-8"))
  
    table = Table(box=None, show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="bold")
  
    table.add_row("ID Сессии:", ctx.session_id[:8])
    table.add_row("Запросов:", str(stats["requests"]))
    table.add_row("Токенов (est):", f"{stats['total_tokens']:,}")
    table.add_row("Длительность:", duration_str)
    table.add_row("Размер Favorite.md:", f"{fav_size} байт")
  
    or_key = ctx.config.default_openrouter_key()
    if or_key:
        table.add_row("Модель:", or_key.get("model", "qwen/qwen3-coder:free"))
        table.add_row("Провайдер:", "OpenRouter")
    else:
        fav_key = ctx.config.default_favorite_key()
        if fav_key:
            table.add_row("Модель:", fav_key.get("model", "gemini"))
            table.add_row("Провайдер:", "FavoriteAPI")
  
    console.print(Panel(table, title="[bold #ff8c00]Статистика использования[/bold #ff8c00]", expand=False))
  
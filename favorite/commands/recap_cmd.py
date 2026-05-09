"""
/recap — краткий дайджест текущей сессии.
Показывает последние N сообщений в компактном виде без переспама.
"""
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .base import ICommand, CommandContext
from ..ui.chat import print_separator, print_status_line

console = Console()
_DEFAULT_LINES = 6


class RecapCommand(ICommand):
  name = "/recap"
  description = "Краткий дайджест сессии"
  priority = 12

  def execute(self, args: str, ctx: CommandContext) -> None:
    from ..sessions.manager import SessionManager
  
    try:
        n = int(args.strip()) if args.strip().isdigit() else _DEFAULT_LINES
    except ValueError:
        n = _DEFAULT_LINES
  
    mgr = SessionManager()
    history = mgr.load_history(ctx.session_id)
  
    if not history:
        print_status_line("Recap", "история пуста", color="#666666")
        return
  
    # Берём последние n пар user/agent
    entries = [e for e in history if e.get("type") in ("user", "agent", "assistant")]
    recent  = entries[-(n * 2):]
  
    lines: list[str] = []
    for e in recent:
        role    = e.get("type", "")
        content = (e.get("content") or "").strip()
  
        # Compact: first 120 chars of each turn
        snippet = content[:120].replace("\n", " ")
        if len(content) > 120:
            snippet += "…"
  
        if role == "user":
            lines.append(f"**Ты:** {snippet}")
        else:
            lines.append(f"**AI:**  {snippet}")
  
    meta = mgr.get_session(ctx.session_id)
    stats = (meta or {}).get("stats", {})
    req   = stats.get("requests", 0)
    tok   = stats.get("total_tokens", 0)
    footer = f"\n\n---\n*{req} запросов • ~{tok:,} токенов • сессия `{ctx.session_id[:8]}`*"
  
    print_separator()
    console.print(Panel(
        Markdown("\n\n".join(lines) + footer),
        title=f"[bold #ff8c00]Recap — последние {len(recent)//2 or 1} обменов[/bold #ff8c00]",
        expand=False,
    ))
    print_separator()
  
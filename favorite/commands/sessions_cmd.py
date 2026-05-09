from .base import ICommand, CommandContext
from ..ui.chat import print_agent_message, print_separator, print_status_line
from ..ui.welcome import print_info
from ..sessions.manager import SessionManager


class NewSessionCommand(ICommand):
  name = "/new session"
  description = "Начать новую сессию"
  priority = 6

  def execute(self, args: str, ctx: CommandContext) -> None:
    mgr = SessionManager()
    print_status_line("New Session", "создаю...", color="#ff8c00")
    sid = mgr.create_session(workdir=ctx.workdir)
    print_status_line("New Session", sid[:8], color="#ff8c00")
  

class SessionCommand(ICommand):
  name = "/session"
  description = "Список сохранённых сессий"
  priority = 7

  def execute(self, args: str, ctx: CommandContext) -> None:
    mgr = SessionManager()
    sessions = mgr.list_sessions()
    print_separator()
    print_agent_message("Сохранённые сессии", "system")
    if not sessions:
        print_info("  Сессий нет.")
    for i, s in enumerate(sessions, 1):
        created = s.get("created_at", "?")[:16] if s.get("created_at") else "?"
        title = s.get("title", "без названия")
        print_status_line(
            s["session_id"][:8],
            f"{title}  •  {created}",
            color="#888888",
        )
    print_separator()
  
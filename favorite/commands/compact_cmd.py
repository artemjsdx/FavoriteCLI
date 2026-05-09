"""
/compact — сжать историю сессии в context_summary.md.
Оставляет краткий summary вместо полной истории, освобождая контекст.
"""
from pathlib import Path
from datetime import datetime, timezone

from rich.console import Console

from .base import ICommand, CommandContext
from ..ui.chat import print_separator, print_status_line

console = Console()


def _build_summary(history: list[dict]) -> str:
  """Собирает краткий текстовый summary из истории."""
  lines = ["# Context Summary", f"_Сжато: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_", ""]
  user_msgs, agent_msgs = 0, 0
  topics: list[str] = []

  for e in history:
      role    = e.get("type", "")
      content = (e.get("content") or "").strip()
      if role == "user":
          user_msgs += 1
          snippet = content[:100].replace("\n", " ")
          topics.append(f"- **Пользователь:** {snippet}")
      elif role in ("agent", "assistant"):
          agent_msgs += 1
          snippet = content[:120].replace("\n", " ")
          topics.append(f"  **AI:** {snippet}")

  lines.append(f"**Всего:** {user_msgs} вопросов пользователя, {agent_msgs} ответов AI")
  lines.append("")
  lines += topics[:60]  # cap at 60 items
  if len(topics) > 60:
      lines.append(f"_...и ещё {len(topics)-60} обменов (скрыто для экономии контекста)_")

  return "\n".join(lines)


class CompactCommand(ICommand):
  name = "/compact"
  description = "Сжать историю в context_summary.md"
  priority = 13

  def execute(self, args: str, ctx: CommandContext) -> None:
      from ..sessions.manager import SessionManager

      mgr     = SessionManager()
      history = mgr.load_history(ctx.session_id)

      if not history:
          print_status_line("Compact", "история пуста — нечего сжимать", color="#666666")
          return

      original_count = len(history)

      # Build summary text
      summary = _build_summary(history)

      # Write context_summary.md into session dir
      sessions_base = Path(__file__).resolve().parent.parent.parent / "sessions"
      session_dir   = sessions_base / ctx.session_id
      session_dir.mkdir(parents=True, exist_ok=True)
      summary_path  = session_dir / "context_summary.md"
      summary_path.write_text(summary, encoding="utf-8")

      # Overwrite history.jsonl with a single synthetic summary entry
      import json
      compact_entry = {
          "type": "system",
          "content": f"[compact summary — предыдущая история сжата. См. context_summary.md]\n\n{summary}",
      }
      history_path = session_dir / "history.jsonl"
      history_path.write_text(
          json.dumps(compact_entry, ensure_ascii=False) + "\n",
          encoding="utf-8",
      )

      print_separator()
      print_status_line(
          "Compact",
          f"{original_count} записей → 1 summary  •  {summary_path.name}",
          color="#ff8c00",
      )
      console.print(
          f"  [dim]Полный лог сохранён в:[/dim] [#ff8c00]{summary_path}[/#ff8c00]"
      )
      print_separator()

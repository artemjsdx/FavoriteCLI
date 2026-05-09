"""
favorite/commands/architect_cmd.py — /architect command.
Premium model thinks → cheap model executes (§19.1 menu principle).
"""
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape
from rich.prompt import Prompt
from .base import ICommand, CommandContext

console = Console()

_DEFAULT_THINK_MODEL = "google/gemini-2.0-flash-thinking-exp:free"
_DEFAULT_EXEC_MODEL = "qwen/qwen3-coder:free"

_ARCHITECT_SYSTEM = (
  "You are a senior software architect. Given a task, produce a detailed step-by-step plan. "
  "Each step should be concrete and executable by an AI coding agent. "
  "Use numbered steps. Be thorough but concise."
)


class ArchitectCommand(ICommand):
  name = "/architect"
  description = "Режим Архитектора: дорогая модель думает, дешёвая делает"
  priority = 14

  def execute(self, args: str, ctx: CommandContext) -> None:
      self._show_menu(args.strip(), ctx)

  def _show_menu(self, task: str, ctx: CommandContext) -> None:
      think_model, exec_model = self._load_config(ctx)
      console.print()
      console.print(Panel(
          "[bold #ff8c00]Режим Архитектора[/bold #ff8c00]\n\n"
          "[dim]Дорогая модель составит детальный план,\n"
          "затем дешёвая модель его реализует.[/dim]\n\n"
          f"  Think:   [dim]{think_model}[/dim]\n"
          f"  Execute: [dim]{exec_model}[/dim]\n\n"
          "  1. Запустить (ввести задачу)\n"
          "  2. Настройки моделей\n"
          "  3. Отмена\n\n"
          "  [dim]arrows — выбор   1..3 — быстро   Enter — ок   ESC — назад[/dim]",
          border_style="#ff8c00"
      ))
      choice = Prompt.ask("  Выбор", choices=["1", "2", "3"], default="1")
      if choice == "3":
          return
      if choice == "2":
          self._settings(ctx)
          return
      if not task:
          task = Prompt.ask("  Задача для Архитектора")
      if task.strip():
          self._run(task, ctx)

  def _load_config(self, ctx: CommandContext) -> tuple:
      try:
          from ..sessions.manager import SessionManager
          sm = SessionManager()
          sess_dir = sm.current_session_dir()
          if sess_dir:
              conf = Path(sess_dir) / "architect_config.json"
              if conf.exists():
                  data = json.loads(conf.read_text())
                  return (
                      data.get("think_model", _DEFAULT_THINK_MODEL),
                      data.get("execute_model", _DEFAULT_EXEC_MODEL),
                  )
      except Exception:
          pass
      return _DEFAULT_THINK_MODEL, _DEFAULT_EXEC_MODEL

  def _settings(self, ctx: CommandContext) -> None:
      think_model, exec_model = self._load_config(ctx)
      think = Prompt.ask("  Модель для планирования", default=think_model)
      execute = Prompt.ask("  Модель для исполнения", default=exec_model)
      try:
          from ..sessions.manager import SessionManager
          sm = SessionManager()
          sess_dir = sm.current_session_dir()
          if sess_dir:
              conf = Path(sess_dir) / "architect_config.json"
              conf.write_text(json.dumps({
                  "think_model": think,
                  "execute_model": execute,
              }))
              console.print("  [dim #888888]Настройки сохранены[/dim #888888]")
      except Exception as e:
          console.print(f"  [yellow]Не удалось сохранить: {e}[/yellow]")

  def _run(self, task: str, ctx: CommandContext) -> None:
      think_model, exec_model = self._load_config(ctx)
      cfg = ctx.config

      console.print(f"\n  [bold #ff8c00]АРХИТЕКТОР[/bold #ff8c00] [dim]({think_model})[/dim]")
      console.print(f"  [dim #888888]Планирую: {escape(task[:80])}[/dim #888888]")
      try:
          plan = self._call_llm(task, _ARCHITECT_SYSTEM, think_model, cfg)
      except Exception as e:
          console.print(f"  [red]Ошибка планирования: {e}[/red]")
          return

      console.print(Panel(
          escape(plan[:400]) + ("..." if len(plan) > 400 else ""),
          title="[bold]План Архитектора[/bold]",
          border_style="dim"
      ))

      exec_system = (
          f"You are an execution agent. Execute the following architect plan step by step.\n\n"
          f"PLAN:\n{plan}\n\n"
          f"Use SHELL_RAW, WRITE_FILE, and other available tags to implement each step. "
          f"Original task: {task}"
      )
      console.print(f"\n  [bold #ff8c00]ИСПОЛНИТЕЛЬ[/bold #ff8c00] [dim]({exec_model})[/dim]")
      console.print("  [dim]Реализую план...[/dim]")
      try:
          response = self._call_llm("Execute the plan now.", exec_system, exec_model, cfg)
          try:
              from ..agent.tags import extract_tags
              from ..agent.executor import execute_tags_with_output
              tags = extract_tags(response)
              if tags:
                  execute_tags_with_output(tags, ctx, cfg)
          except Exception:
              pass
          try:
              from ..agent.tags import strip_tags
              clean = strip_tags(response)
          except Exception:
              clean = response
          from ..ui.chat import print_agent_message
          print_agent_message(clean, "main")
      except Exception as e:
          console.print(f"  [red]Ошибка исполнения: {e}[/red]")

  def _call_llm(self, user_msg: str, system: str, model: str, cfg) -> str:
      import urllib.request
      or_key = cfg.default_openrouter_key()
      if not or_key:
          raise RuntimeError("Нужен OpenRouter ключ")
      payload = json.dumps({
          "model": model,
          "messages": [
              {"role": "system", "content": system},
              {"role": "user", "content": user_msg},
          ],
          "stream": False,
      }).encode("utf-8")
      req = urllib.request.Request(
          "https://openrouter.ai/api/v1/chat/completions",
          data=payload,
          headers={
              "Authorization": f"Bearer {or_key['key']}",
              "Content-Type": "application/json",
          },
          method="POST"
      )
      with urllib.request.urlopen(req, timeout=60) as resp:
          data = json.loads(resp.read().decode("utf-8"))
      return data["choices"][0]["message"]["content"]

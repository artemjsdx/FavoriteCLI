"""
favorite/commands/effort_cmd.py — /effort command.
Estimates task complexity using the current main agent model.
"""
import json
import re
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()

_EFFORT_SYSTEM = (
  "You are a task complexity estimator for a software AI agent. "
  "Given a task description, respond ONLY with valid JSON (no markdown, no explanation): "
  '{"complexity": "low|medium|high|expert", '
  '"time_min": <int>, "time_max": <int>, "time_unit": "minutes|hours", '
  '"recommended_roles": ["role_id1", "role_id2"], '
  '"risks": ["risk1", "risk2", "risk3"], '
  '"first_step": "concrete first action"}'
)

_COLORS = {"low": "green", "medium": "yellow", "high": "red", "expert": "bold red"}
_LABELS = {"low": "Низкая", "medium": "Средняя", "high": "Высокая", "expert": "Экспертная"}


class EffortCommand(ICommand):
  name = "/effort"
  description = "Оценить сложность задачи"
  priority = 12

  def execute(self, args: str, ctx: CommandContext) -> None:
      task = args.strip()
      if not task:
          hist = getattr(ctx, "history", [])
          for msg in reversed(hist):
              if msg.get("role") == "user":
                  task = msg.get("content", "").strip()
                  break
      if not task:
          console.print("  [dim]Укажи задачу: /effort <описание задачи>[/dim]")
          return

      console.print(f"  [dim #888888]Оцениваю: {escape(task[:60])}...[/dim #888888]")
      try:
          result = self._evaluate(task, ctx)
          self._render(task, result)
      except Exception as e:
          console.print(f"  [red]Ошибка оценки: {e}[/red]")

  def _evaluate(self, task: str, ctx: CommandContext) -> dict:
      cfg = ctx.config
      or_key = cfg.default_openrouter_key()
      if not or_key:
          raise RuntimeError("Нужен OpenRouter ключ")

      import urllib.request
      import urllib.error
      model = or_key.get("model", "qwen/qwen3-coder:free")
      payload = json.dumps({
          "model": model,
          "messages": [
              {"role": "system", "content": _EFFORT_SYSTEM},
              {"role": "user", "content": f"Task: {task}"},
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
      with urllib.request.urlopen(req, timeout=30) as resp:
          data = json.loads(resp.read().decode("utf-8"))
      raw = data["choices"][0]["message"]["content"]
      m = re.search(r'\{.*?\}', raw, re.DOTALL)
      if not m:
          raise ValueError(f"No JSON in response: {raw[:200]}")
      return json.loads(m.group(0))

  def _render(self, task: str, r: dict) -> None:
      complexity = r.get("complexity", "medium")
      color = _COLORS.get(complexity, "white")
      label = _LABELS.get(complexity, complexity)
      t_min = r.get("time_min", "?")
      t_max = r.get("time_max", "?")
      unit = r.get("time_unit", "minutes")
      unit_ru = "мин" if unit == "minutes" else "ч"
      roles = r.get("recommended_roles", [])
      risks = r.get("risks", [])
      first = r.get("first_step", "")

      lines = [
          f"Задача: [dim]{escape(task[:80])}[/dim]",
          f"Сложность: [{color}]{label}[/{color}]",
          f"Время: {t_min}\u2013{t_max} {unit_ru}",
      ]
      if roles:
          lines.append(f"Роли: [cyan]{', '.join(roles)}[/cyan]")
      if risks:
          lines.append("Риски:")
          for risk in risks[:3]:
              lines.append(f"  - [yellow]{escape(risk)}[/yellow]")
      if first:
          lines.append(f"Первый шаг: [dim]{escape(first)}[/dim]")

      console.print(Panel(
          "\n".join(lines),
          title="[bold #ff8c00]Оценка задачи[/bold #ff8c00]",
          border_style="#ff8c00"
      ))

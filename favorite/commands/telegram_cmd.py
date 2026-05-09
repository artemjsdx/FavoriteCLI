"""
favorite/commands/telegram_cmd.py — /telegram command.
Menu-driven Telegram notification settings (per §19.1 principle).
"""
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from .base import ICommand, CommandContext

console = Console()


class TelegramCommand(ICommand):
  name = "/telegram"
  description = "Настройки Telegram-уведомлений"
  priority = 15

  def execute(self, args: str, ctx: CommandContext) -> None:
      notifier = getattr(ctx, "telegram", None)
      if notifier is None:
          console.print(
              "  [yellow]Telegram не инициализирован. Проверь config/telegram.json.[/yellow]"
          )
          return
      self._main_menu(notifier)

  def _main_menu(self, notifier) -> None:
      while True:
          status = "[green]вкл[/green]" if notifier.enabled else "[dim]выкл[/dim]"
          console.print()
          console.print(Panel(
              f"[bold #ff8c00]Telegram-уведомления[/bold #ff8c00]  {status}\n\n"
              "  1. Подключение (токен + получатели)\n"
              "  2. Режим роутинга\n"
              "  3. События (галочки)\n"
              "  4. Тест соединения\n"
              "  5. Тихий час\n"
              "  6. Включить / выключить\n"
              "  7. Выход\n\n"
              "  [dim]arrows — выбор   1..7 — быстро   Enter — ок   ESC — назад[/dim]",
              border_style="#ff8c00"
          ))
          choice = Prompt.ask("  Выбор", choices=["1","2","3","4","5","6","7"], default="7")
          if choice == "7":
              break
          elif choice == "1":
              self._setup_connection(notifier)
          elif choice == "2":
              self._setup_routing(notifier)
          elif choice == "3":
              self._setup_events(notifier)
          elif choice == "4":
              self._test_connection(notifier)
          elif choice == "5":
              self._setup_quiet_hours(notifier)
          elif choice == "6":
              self._toggle(notifier)

  def _setup_connection(self, notifier) -> None:
      console.print("\n  [bold]Настройка подключения[/bold]")
      token = Prompt.ask(
          "  Bot token (Enter — оставить текущий)", default="", show_default=False
      )
      if token.strip():
          notifier._cfg["bot_token"] = token.strip()
      recipients_str = Prompt.ask(
          "  Получатели (chat_id через запятую, Enter — оставить)",
          default="", show_default=False
      )
      if recipients_str.strip():
          parts = [p.strip() for p in recipients_str.split(",") if p.strip()]
          processed = []
          for p in parts:
              try:
                  processed.append(int(p))
              except ValueError:
                  processed.append(p)
          notifier._cfg["recipients"] = processed
      notifier.save_config()
      console.print("  [dim #888888]Сохранено[/dim #888888]")

  def _setup_routing(self, notifier) -> None:
      console.print("\n  [bold]Режим роутинга[/bold]")
      console.print("  1. log_only  — только локальный лог (без Telegram)")
      console.print("  2. private   — в личку боту")
      console.print("  3. group     — в группу")
      console.print("  4. channel   — в канал")
      current = notifier._cfg.get("routing", "log_only")
      console.print(f"  [dim]Текущий: {current}[/dim]")
      choice = Prompt.ask("  Режим", choices=["1","2","3","4"], default="1")
      modes = {"1": "log_only", "2": "private", "3": "group", "4": "channel"}
      notifier._cfg["routing"] = modes[choice]
      notifier.save_config()
      console.print(f"  [dim #888888]Режим: {modes[choice]}[/dim #888888]")

  def _setup_events(self, notifier) -> None:
      events = notifier._cfg.get("events", {})
      labels = {
          "final_answers": "Финальные ответы (обязательно)",
          "main_thoughts": "Мысли главного агента",
          "sub_replies": "Реплики суб-агентов",
          "system_events": "Системные события",
          "votes": "Голосования",
          "checkpoints": "Чек-пойнты /auto",
          "steps": "Каждый шаг (STEP)",
          "questions": "Вопросы к пользователю (обязательно)",
      }
      fixed = {"final_answers", "questions"}
      console.print("\n  [bold]Настройка событий[/bold]")
      for key, label in labels.items():
          if key in fixed:
              console.print(f"  [dim]  {label}: [green]вкл[/green] (нельзя выключить)[/dim]")
              continue
          current = events.get(key, False)
          toggle = Confirm.ask(f"  {label}", default=current)
          events[key] = toggle
      notifier._cfg["events"] = events
      notifier.save_config()
      console.print("  [dim #888888]Настройки событий сохранены[/dim #888888]")

  def _test_connection(self, notifier) -> None:
      console.print("  [dim]Отправляю тест...[/dim]")
      ok = notifier.test_connection()
      if ok:
          console.print("  [green]Тест прошёл успешно[/green]")
      else:
          console.print("  [red]Ошибка. Проверь bot_token и ID получателей.[/red]")

  def _setup_quiet_hours(self, notifier) -> None:
      console.print("\n  [bold]Тихий час[/bold]")
      console.print("  В это время отправляются только обязательные события.")
      enable = Confirm.ask("  Включить тихий час?", default=False)
      if enable:
          start = Prompt.ask("  Начало (час 0-23)", default="23")
          end = Prompt.ask("  Конец (час 0-23)", default="8")
          notifier._cfg["quiet_hours"] = {"start": int(start), "end": int(end)}
      else:
          notifier._cfg["quiet_hours"] = None
      notifier.save_config()
      console.print("  [dim #888888]Сохранено[/dim #888888]")

  def _toggle(self, notifier) -> None:
      current = notifier._cfg.get("enabled", False)
      notifier._cfg["enabled"] = not current
      notifier.save_config()
      state = "включены" if not current else "выключены"
      console.print(f"  [dim]Уведомления {state}[/dim]")

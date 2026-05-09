"""
favorite/commands/tour_cmd.py — /tour command (§17.21).
Restarts the onboarding tour so the user can re-read usage tips.
"""
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()
_SEP = "[dim #2a2a2a]" + "─" * 50 + "[/dim #2a2a2a]"

_TOUR_STEPS = [
    ("Привет! Это Favorite CLI — твой AI-агент прямо в терминале.", None),
    ("Основные команды:", [
        "/help       — список всех команд",
        "/models     — выбор модели",
        "/agents     — управление суб-агентами",
        "/memory     — заметки и память агента",
    ]),
    ("Режимы работы:", [
        "/auto       — автономный режим (агент решает сам)",
        "/build      — режим выполнения задач",
        "/plan       — режим планирования",
        "/silent     — без подтверждений",
    ]),
    ("Параллельность:", [
        "/parallel unified <задача>     — все агенты на одну задачу",
        "/parallel independent <задача> — каждому агенту свой кусок",
        "/parallel hybrid <задача>      — координатор + воркеры",
    ]),
    ("Память и сессии:", [
        "/snapshot   — сохранить состояние",
        "/rollback   — вернуться к снапшоту",
        "/compact    — сжать контекст (авто при ~80%)",
        "/recap      — краткая сводка сессии",
    ]),
    ("Агентная сеть:", [
        "Теги в ответе агента:",
        "  <SUB_AGENT:role=coder>задача</SUB_AGENT>",
        "  <SUB_AGENT:role=coder sandbox=true>задача</SUB_AGENT>",
        "  <VOTE:question=Деплоить? timeout=20>да|нет</VOTE>",
        "  <ASK_PEER:to=agent-2>вопрос</ASK_PEER>",
        "  <DELEGATE_PEER:to=agent-2>задача</DELEGATE_PEER>",
        "  <IMAGE:path=screen.png>Что на этом изображении?</IMAGE>",
    ]),
    ("Тур завершён!", [
        "Введи /help для полного списка команд",
        "Введи /agents чтобы создать первого суб-агента",
        "Нажми Ctrl+C чтобы выйти",
    ]),
]


class TourCommand(ICommand):
    name = "/tour"
    description = "Перезапустить онбординг-тур (§17.21)"
    priority = 50

    def execute(self, args: str, ctx: CommandContext) -> None:
        _run_tour()


def _run_tour() -> None:
    from ..ui.chat import print_separator
    print_separator()
    console.print()
    console.print("  [bold #ff8c00]◈ TOUR[/bold #ff8c00]  [dim]Добро пожаловать в Favorite CLI[/dim]")
    console.print()

    for i, step in enumerate(_TOUR_STEPS):
        title, items = step if len(step) == 2 else (step[0], None)

        num = f"[dim #666666]{i+1}/{len(_TOUR_STEPS)}[/dim #666666]"
        console.print(f"  {num}  [bold white]{escape(title)}[/bold white]")

        if items:
            for item in items:
                if item.startswith("  "):
                    console.print(f"        [dim #888888]{escape(item.strip())}[/dim #888888]")
                elif item.startswith("/") or item.startswith("<"):
                    console.print(f"      [bold cyan]{escape(item)}[/bold cyan]")
                else:
                    console.print(f"      [dim #aaaaaa]{escape(item)}[/dim #aaaaaa]")

        console.print()

        if i < len(_TOUR_STEPS) - 1:
            try:
                input("  [Enter — следующий шаг, Ctrl+C — выход] ")
            except (EOFError, KeyboardInterrupt):
                console.print()
                console.print("  [dim]Тур прерван.[/dim]")
                print_separator()
                return

    print_separator()

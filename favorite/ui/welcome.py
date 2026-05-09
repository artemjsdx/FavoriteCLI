import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

try:
    import pyfiglet
    _HAS_FIGLET = True
except ImportError:
    _HAS_FIGLET = False

from .theme import ORANGE, WHITE, GRAY, LOGO_FONT

console = Console()


def clear_screen() -> None:
    os.system("clear")


def _make_banner() -> str:
    if _HAS_FIGLET:
        raw = pyfiglet.figlet_format("FAVORITE", font=LOGO_FONT)
    # Убираем пустые строки сверху и снизу
        lines = raw.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)
# Фолбэк если pyfiglet не установлен
    return "F A V O R I T E"


def render_welcome(model_name: str, workdir: str) -> None:
    max_path = 44
    display_path = workdir if len(workdir) <= max_path else "…" + workdir[-(max_path - 1):]
    
    banner = _make_banner()
    
    content = Text(justify="center")
    content.append("\n")
    content.append(banner, style=f"bold {ORANGE}")
    content.append("\n\n")
    content.append(model_name, style=f"bold {WHITE}")
    content.append("\n")
    content.append(display_path, style=GRAY)
    content.append("\n")
    
    panel = Panel(
        content,
        title="[bold #ff8c00]Favorite Code[/bold #ff8c00]",
        border_style=f"bold {ORANGE}",
        padding=(0, 2),
        width=58,
    )
    console.print(Align.center(panel))
    console.print()


def render_separator() -> None:
    console.print("\u2500" * 50, style=GRAY)


def print_agent_dot(text: str) -> None:
    console.print(f"[bold {ORANGE}]\u25cf[/bold {ORANGE}] {text}")


def print_step(text: str) -> None:
    for line in text.strip().splitlines():
        console.print(f"  [dim]\u23ce  {line}[/dim]")


def print_error(text: str) -> None:
    console.print(f"[bold red]ERROR:[/bold red] {text}")


def print_info(text: str) -> None:
    console.print(text)

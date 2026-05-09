"""
favorite/commands/mode_cmd.py — /mode command.
Switch agent operating mode: lite | pro | max
"""
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()

_MODULES_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "modules.json"
_MODE_FILE    = Path(__file__).resolve().parent.parent.parent / "config" / "mode.json"

MODES = {
    "lite": {
        "display": "Lite",
        "color": "#4a9eff",
        "icon": "◆",
        "description": "Осторожный. Уточняет перед каждым действием. Для важных данных.",
        "modules": {
            "action_bias_mode":         "cautious",
            "verifier_mode":            "auto",
            "context_compaction_mode":  "manual",
            "auto_checkpoint_interval": 3,
            "max_sub_agent_depth":      1,
            "auto_parallelism_mode":    "unified",
            "shell_output_limit":       "fixed",
            "agent_mode":               "lite",
        },
    },
    "pro": {
        "display": "Pro",
        "color": "#ff8c00",
        "icon": "◈",
        "description": "Сбалансированный. Действует сам, уточняет только перед деструктивным.",
        "modules": {
            "action_bias_mode":         "balanced",
            "verifier_mode":            "tag",
            "context_compaction_mode":  "auto",
            "auto_checkpoint_interval": 10,
            "max_sub_agent_depth":      3,
            "auto_parallelism_mode":    "unified",
            "shell_output_limit":       "fixed",
            "agent_mode":               "pro",
        },
    },
    "max": {
        "display": "Max",
        "color": "#ff3333",
        "icon": "◉",
        "description": "Максимальная автономия. Никогда не сдаётся. Исследует среду, ставит пакеты, параллельные субагенты.",
        "modules": {
            "action_bias_mode":         "aggressive",
            "verifier_mode":            "off",
            "context_compaction_mode":  "aggressive",
            "auto_checkpoint_interval": 20,
            "max_sub_agent_depth":      5,
            "auto_parallelism_mode":    "independent",
            "shell_output_limit":       "auto",
            "agent_mode":               "max",
        },
    },
}


def _load_modules() -> dict:
    if _MODULES_FILE.exists():
        try:
            return json.loads(_MODULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_modules(data: dict) -> None:
    _MODULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MODULES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_current_mode() -> str:
    if _MODE_FILE.exists():
        try:
            return json.loads(_MODE_FILE.read_text(encoding="utf-8")).get("mode", "pro")
        except Exception:
            pass
    return "pro"


def _set_mode(mode_id: str) -> None:
    _MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MODE_FILE.write_text(
        json.dumps({"mode": mode_id}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    data = _load_modules()
    data.update(MODES[mode_id]["modules"])
    _save_modules(data)


class ModeCommand(ICommand):
    name = "/mode"
    description = "Переключить режим агента: lite | pro | max"
    priority = 5

    def execute(self, args: str, ctx: CommandContext) -> None:
        arg = args.strip().lower()
        current = _get_current_mode()

        if not arg:
            self._show_status(current)
            return

        if arg not in MODES:
            console.print(f"  [red]Неизвестный режим: {escape(arg)}[/red]")
            console.print("  Доступные: [bold]lite[/bold] | [bold]pro[/bold] | [bold]max[/bold]")
            return

        if arg == current:
            m = MODES[arg]
            console.print(
                f"  [dim]Уже в режиме [{m['color']}]{m['icon']} {m['display']}[/{m['color']}][/dim]"
            )
            return

        _set_mode(arg)
        m = MODES[arg]
        console.print()
        console.print(Panel(
            f"[bold {m['color']}]{m['icon']} {m['display']}[/bold {m['color']}]\n\n{m['description']}",
            title="[bold]Режим переключён[/bold]",
            border_style=m["color"],
            padding=(0, 2),
        ))
        console.print()
        for k, v in MODES[arg]["modules"].items():
            if k != "agent_mode":
                console.print(f"  [dim]  {k}: [bold]{v}[/bold][/dim]")
        console.print()

    def _show_status(self, current: str) -> None:
        table = Table(show_header=True, header_style="bold #ff8c00", box=None, padding=(0, 2))
        table.add_column("", width=3)
        table.add_column("Режим", width=8)
        table.add_column("Описание")
        table.add_column("Статус", width=10)

        for mid, m in MODES.items():
            active = mid == current
            status = (
                f"[bold {m['color']}]● активен[/bold {m['color']}]"
                if active else "[dim]○[/dim]"
            )
            name_str = (
                f"[bold {m['color']}]{m['icon']} {m['display']}[/bold {m['color']}]"
                if active else f"[dim]{m['icon']} {m['display']}[/dim]"
            )
            table.add_row("", name_str, f"[dim]{m['description']}[/dim]", status)

        console.print()
        console.print(table)
        console.print()
        console.print("  [dim]Переключить: /mode lite | /mode pro | /mode max[/dim]")
        console.print()

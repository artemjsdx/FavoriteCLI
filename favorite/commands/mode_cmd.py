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
        "description": "Быстро и коротко. Минимум рассуждений. Минимум токенов. Сразу к делу.",
        "modules": {
            "action_bias_mode":         "fast",
            "verifier_mode":            "off",
            "context_compaction_mode":  "aggressive",
            "auto_checkpoint_interval": 5,
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
        "description": "Баланс скорости и глубины. Рассуждает там где нужно, не тормозит где не нужно.",
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
        "description": "Глубокий анализ. Тщательное рассуждение. Берёт время — даёт точный результат.",
        "modules": {
            "action_bias_mode":         "thorough",
            "verifier_mode":            "deep",
            "context_compaction_mode":  "manual",
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


def _announce_mode(mode_id: str) -> None:
      m = MODES[mode_id]
      c = m["color"]
      console.print()
      console.print(f"  [{c}]│[/{c}] [bold {c}]{m['icon']} {m['display'].upper()}[/bold {c}]")
      console.print(f"  [{c}]│[/{c}]")
      console.print(f"  [{c}]│[/{c}]  [dim #aaaaaa]{m['description']}[/dim #aaaaaa]")
      console.print(f"  [{c}]│[/{c}]")
      console.print()


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
        ctx.current_mode = arg  # §PATCH-1
        _announce_mode(arg)

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
        console.print("  [dim]Или быстро: /lite | /pro | /max[/dim]")
        console.print()


class _ModeShortcut(ICommand):
    """Базовый класс для быстрых /lite /pro /max команд."""
    _mode_id: str = ""
    priority = 5

    def execute(self, args: str, ctx: CommandContext) -> None:
        current = _get_current_mode()
        if self._mode_id == current:
            m = MODES[self._mode_id]
            console.print(
                f"  [dim]Уже в режиме [{m['color']}]{m['icon']} {m['display']}[/{m['color']}][/dim]"
            )
            return
        _set_mode(self._mode_id)
        ctx.current_mode = self._mode_id  # §PATCH-1
        _announce_mode(self._mode_id)


class LiteCommand(_ModeShortcut):
    name = "/lite"
    description = "Переключить в режим Lite (быстро, минимум рассуждений)"
    _mode_id = "lite"


class ProCommand(_ModeShortcut):
    name = "/pro"
    description = "Переключить в режим Pro (баланс скорости и глубины)"
    _mode_id = "pro"


class MaxCommand(_ModeShortcut):
    name = "/max"
    description = "Переключить в режим Max (глубокий анализ, тщательный результат)"
    _mode_id = "max"

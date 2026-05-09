"""
favorite/commands/model_router_cmd.py — /model-router command (§40).
Enable/disable automatic model selection based on request complexity.
"""
import json
from pathlib import Path
from rich.console import Console
from .base import ICommand, CommandContext

console = Console()
_CFG_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "modules.json"


def _get_router_cfg() -> dict:
    if _CFG_FILE.exists():
        try:
            data = json.loads(_CFG_FILE.read_text(encoding="utf-8"))
            return data.get("model_router", {})
        except Exception:
            pass
    return {}


def _set_router_enabled(enabled: bool) -> None:
    if not _CFG_FILE.exists():
        return
    try:
        data = json.loads(_CFG_FILE.read_text(encoding="utf-8"))
        if "model_router" not in data:
            data["model_router"] = {}
        data["model_router"]["enabled"] = enabled
        _CFG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


class ModelRouterCommand(ICommand):
    name = "/model-router"
    description = "Авто-маршрутизация модели по сложности запроса (§40)"
    priority = 75

    def execute(self, args: str, ctx: CommandContext) -> None:
        args = (args or "").strip().lower()
        cfg = _get_router_cfg()
        enabled = cfg.get("enabled", False)

        if not args:
            status = "[green]включён[/green]" if enabled else "[dim]выключен[/dim]"
            simple_model = cfg.get("simple_model", "не задана")
            console.print(f"  Model Router: {status}")
            console.print(f"  Быстрая модель: [dim]{simple_model}[/dim]")
            console.print("  [dim]/model-router on | off | status[/dim]")
        elif args == "on":
            _set_router_enabled(True)
            console.print("  [dim #666666]Model Router включён — простые запросы → лёгкая модель[/dim #666666]")
        elif args == "off":
            _set_router_enabled(False)
            console.print("  [dim #666666]Model Router выключен — всегда используется основная модель[/dim #666666]")
        elif args == "status":
            status = "включён" if enabled else "выключен"
            console.print(f"  Model Router: {status}")
            console.print(f"  [dim]{json.dumps(cfg, indent=2, ensure_ascii=False)}[/dim]")
        else:
            console.print("  [dim]Использование: /model-router on | off | status[/dim]")

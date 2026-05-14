from rich.console import Console
from rich.markup import escape
from datetime import datetime, timezone
from .base import ICommand, CommandContext
from ..memory.favorite_md import _DEFAULT as FAV_MD_PATH

console = Console()

ORANGE = "#ff8c00"
DIM    = "#555555"
DIM2   = "#333333"

class UsageCommand(ICommand):
  name = "/usage"
  description = "Показать статистику использования сессии"
  priority = 10

  def execute(self, args: str, ctx: CommandContext) -> None:
    from ..sessions.manager import SessionManager
    mgr = SessionManager()
    meta = mgr.get_session(ctx.session_id)

    if not meta:
        console.print("[red]Сессия не найдена.[/red]")
        return

    stats = meta.get("stats", {
        "total_tokens": 0,
        "requests": 0,
        "start_time": meta.get("created_at")
    })

    start_dt = datetime.fromisoformat(stats["start_time"])
    now = datetime.now(timezone.utc)
    duration = now - start_dt
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = f"{hours}ч {minutes}м {seconds}с"

    fav_size = 0
    if FAV_MD_PATH.exists():
        fav_size = len(FAV_MD_PATH.read_text(encoding="utf-8"))

    try:
        from ..agent.model_router import RouterModule as _RM
        _prov, _model, _ = _RM.select_model("", ctx.config)
    except Exception:
        _prov, _model = "—", "—"

    def row(label: str, value: str) -> None:
        pad = " " * max(1, 12 - len(label))
        console.print(f"  [dim {DIM}]{label}[/dim {DIM}]" + pad + f"[white]{value}[/white]")

    console.print()
    console.print(f"  [bold {ORANGE}]USAGE[/bold {ORANGE}]  [dim {DIM2}]" + "─" * 36 + f"[/dim {DIM2}]")
    console.print()
    row("session",   ctx.session_id[:8])
    row("requests",  str(stats["requests"]))
    row("tokens",    f"{stats['total_tokens']:,}")
    row("uptime",    duration_str)
    row("fav.md",    f"{fav_size} байт")
    row("provider",  escape(_prov))
    row("model",     escape(_model))
    console.print()

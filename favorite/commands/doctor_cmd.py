"""
/doctor — быстрая диагностика: API ключи, сеть, воркдир, память.
"""
import socket
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .base import ICommand, CommandContext
from ..ui.chat import print_separator, print_status_line
from ..memory.favorite_md import _DEFAULT as FAV_MD_PATH

console = Console()

_OK   = "[bold green]OK[/bold green]"
_FAIL = "[bold red]FAIL[/bold red]"
_WARN = "[bold yellow]WARN[/bold yellow]"


def _check_net(host: str = "openrouter.ai", port: int = 443, timeout: float = 3.0) -> bool:
  try:
      socket.setdefaulttimeout(timeout)
      with socket.create_connection((host, port)):
          return True
  except OSError:
    return False


class DoctorCommand(ICommand):
  name = "/doctor"
  description = "Диагностика: ключи, сеть, файлы"
  priority = 11

  def execute(self, args: str, ctx: CommandContext) -> None:
    cfg = ctx.config
    print_separator()
    print_status_line("Doctor", "проверяю...", color="#ff8c00")
  
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Check", style="dim", min_width=22)
    table.add_column("Status", min_width=6)
    table.add_column("Detail", style="dim")
  
    # --- Providers ---
    or_key = cfg.default_openrouter_key()
    fav_key = cfg.default_favorite_key()
    nv_key = getattr(cfg, "nvidia_key", None)
  
    table.add_row(
        "OpenRouter ключ",
        _OK if or_key else _WARN,
        or_key.get("model", "") if or_key else "не задан",
    )
    table.add_row(
        "FavoriteAPI ключ",
        _OK if fav_key else _WARN,
        fav_key.get("model", "") if fav_key else "не задан",
    )
    table.add_row(
        "NVIDIA ключ",
        _OK if nv_key else _WARN,
        "задан" if nv_key else "не задан",
    )
    if not or_key and not fav_key:
        table.add_row("Итого провайдеров", _FAIL, "нет ни одного — чат не работает")
    else:
        providers = []
        if or_key:
            providers.append("OpenRouter")
        if fav_key:
            providers.append("FavoriteAPI")
        if nv_key:
            providers.append("NVIDIA")
        table.add_row("Итого провайдеров", _OK, ", ".join(providers))
  
    # --- Network ---
    or_online  = _check_net("openrouter.ai")
    table.add_row("Сеть → openrouter.ai", _OK if or_online else _FAIL, "")
  
    fav_url = getattr(cfg, "favorite_api_base_url", None)
    if fav_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(fav_url)
            h = parsed.hostname or ""
            p = parsed.port or (443 if parsed.scheme == "https" else 80)
            fav_ok = _check_net(h, p)
        except Exception:
            fav_ok = False
        table.add_row(
            f"Сеть → FavoriteAPI",
            _OK if fav_ok else _FAIL,
            fav_url[:50],
        )
  
    # --- Workdir ---
    wd = Path(ctx.workdir)
    table.add_row(
        "Рабочая директория",
        _OK if wd.is_dir() else _FAIL,
        str(wd),
    )
    writable = False
    if wd.is_dir():
        try:
            test_f = wd / ".fav_write_test"
            test_f.write_text("x")
            test_f.unlink()
            writable = True
        except Exception:
            pass
    table.add_row(
        "Запись в workdir",
        _OK if writable else _FAIL,
        "разрешена" if writable else "запрещена",
    )
  
    # --- Memory ---
    fav_exists = FAV_MD_PATH.exists()
    fav_size   = len(FAV_MD_PATH.read_text(encoding="utf-8")) if fav_exists else 0
    table.add_row(
        "Favorite.md",
        _OK if fav_exists else _WARN,
        f"{fav_size} байт" if fav_exists else "не найден",
    )
  
    # --- GitHub ---
    gh_cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "github.json"
    gh_ok = False
    if gh_cfg_path.exists():
        import json
        try:
            gh = json.loads(gh_cfg_path.read_text())
            gh_ok = bool(gh.get("token") and gh.get("repo"))
        except Exception:
            pass
    table.add_row(
        "GitHub конфиг",
        _OK if gh_ok else _WARN,
        "задан" if gh_ok else "не настроен",
    )
  
    console.print(table)
    print_separator()

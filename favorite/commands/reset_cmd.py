"""
favorite/commands/reset_cmd.py
/reset — сброс контекста диалога через FavoriteAPI.
"""
import requests as _req
from rich.console import Console
from rich.text import Text

from .base import ICommand, CommandContext
from ..ui.theme import ORANGE, GRAY
from ..ui.chat import print_status_line

console = Console()


def _is_server_unavailable(result: dict) -> bool:
  """Проверить, вернул ли сервер ошибку недоступности (не настоящий API-ответ)."""
  if result.get("reset") or result.get("requires_choice"):
    return False
  err = result.get("error", "")
  return "недоступен" in err or "Cloudflare" in err or "tunnel" in err.lower()


def _try_refresh_url(cfg) -> bool:
  """Попытаться обновить URL через TG-мост. Возвращает True если URL обновлён."""
  if not cfg.has_tg_bridge():
    return False
  from ..bridge.tg_url import fetch_url, invalidate
  print_status_line("TG Bridge", "ищу новый URL...", color="#666666")
  invalidate()
  fresh_url = fetch_url(cfg.tg_bridge_token, cfg.tg_bridge_chat_id)
  current_url = cfg.favorite_api_base_url
  if fresh_url and fresh_url != current_url:
    cfg.set_favorite_api_base_url(fresh_url)
    print_status_line("TG Bridge", f"новый URL: {fresh_url}", color="#ff8c00")
    return True
  print_status_line("TG Bridge", "новый URL не найден", color="#666666")
  return False


class ResetCommand(ICommand):
  name = "/reset"
  description = "Сбросить контекст диалога (очистить историю на сервере)"
  priority = 25

  def execute(self, args: str, ctx: CommandContext) -> None:
    cfg = ctx.config
    fav_key = cfg.default_favorite_key()
    if not fav_key:
        console.print(f"[bold red]FavoriteAPI не настроен.[/bold red] Добавь ключ через [bold {ORANGE}]/Favorite API[/bold {ORANGE}]")
        return
  
    from ..api.favorite_api import FavoriteApiClient
  
    def _make_client():
        base_url = getattr(cfg, "favorite_api_base_url", FavoriteApiClient.DEFAULT_BASE)
        return FavoriteApiClient(
            api_key=fav_key.get("key", ""),
            base_url=base_url,
            model=fav_key.get("model"),
        )
  
    console.print(f"\n[bold {ORANGE}]●[/bold {ORANGE}] Сброс контекста...")
  
    # ── первая попытка ──────────────────────────────────────────────
    try:
        result = _make_client().reset_context()
    except _req.exceptions.ConnectionError:
        result = None
    except Exception as e:
        console.print(f"[red]Ошибка соединения с FavoriteAPI: {e}[/red]")
        _wait()
        return
  
    # ── сервер недоступен → пробуем обновить URL через TG-мост ─────
    if result is None or _is_server_unavailable(result):
        refreshed = _try_refresh_url(cfg)
        if refreshed:
            try:
                result = _make_client().reset_context()
            except _req.exceptions.ConnectionError:
                result = None
            except Exception as e:
                console.print(f"[red]Ошибка соединения: {e}[/red]")
                _wait()
                return
  
        # всё равно не получилось — сообщаем и выходим
        if result is None or _is_server_unavailable(result):
            err = (result or {}).get("error", "сервер недоступен")
            console.print(f"[red]Не удалось сбросить контекст: {err}[/red]")
            _wait()
            return
  
    # ── сервер требует выбора (контекст переполнен) ─────────────────
    if result.get("requires_choice"):
        _handle_limit_hit(_make_client(), result, ctx)
        return
  
    # ── обычный сброс — успех ───────────────────────────────────────
    if result.get("reset"):
        if ctx.mgr and ctx.session_id:
            ctx.mgr.clear_history(ctx.session_id)
        console.print(f"[bold {ORANGE}]●[/bold {ORANGE}] [dim {GRAY}]Контекст сброшен. История диалога очищена локально и на сервере.[/dim {GRAY}]")
    else:
        err = result.get("error", "неизвестная ошибка")
        console.print(f"[red]Не удалось сбросить контекст: {err}[/red]")
  
    _wait()


    def _handle_limit_hit(client, result: dict, ctx) -> None:
      """Контекст переполнен — спрашиваем что сохранить."""
      files = result.get("files", {})
      ctx_info = files.get("context", {})
      fav_info = files.get("favorite", {})
  
      console.print(f"\n[bold red]Контекст переполнен (~180KB).[/bold red] Выбери что сохранить:\n")
  
      # context.md
      if ctx_info.get("exists"):
        preview = (ctx_info.get("preview") or "")[:80]
        size = ctx_info.get("size_chars", 0)
        console.print(f"  [bold {ORANGE}]context.md[/bold {ORANGE}] ({size} символов)")
        if preview:
            console.print(f"  [dim]  {preview}...[/dim]")
      else:
        console.print(f"  [dim]context.md — пусто[/dim]")
  
      # Favorite.md
      if fav_info.get("exists"):
        preview = (fav_info.get("preview") or "")[:80]
        size = fav_info.get("size_chars", 0)
        console.print(f"  [bold {ORANGE}]Favorite.md[/bold {ORANGE}] ({size} символов)")
        if preview:
            console.print(f"  [dim]  {preview}...[/dim]")
      else:
        console.print(f"  [dim]Favorite.md — пусто[/dim]")
  
      console.print(f"""
      [bold]1.[/bold] Очистить всё (полный сброс)
      [bold]2.[/bold] Сохранить Favorite.md, очистить context
      [bold]3.[/bold] Сохранить оба файла
      [bold]4.[/bold] Отмена
      """)
  
      while True:
        try:
            choice = input("  Выбери [1-4]: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("[dim]Отменено.[/dim]")
            return
  
        if choice == "1":
            ctx_action, fav_action = "clear", "clear"
            break
        elif choice == "2":
            ctx_action, fav_action = "clear", "keep"
            break
        elif choice == "3":
            ctx_action, fav_action = "keep", "keep"
            break
        elif choice == "4":
            console.print("[dim]Отменено.[/dim]")
            return
        else:
            console.print("  [dim]Введи 1, 2, 3 или 4[/dim]")
  
      try:
        apply_result = client.reset_context_apply(context=ctx_action, favorite=fav_action)
      except Exception as e:
        console.print(f"[red]Ошибка применения сброса: {e}[/red]")
        _wait()
        return
  
      if apply_result.get("reset"):
        if ctx.mgr and ctx.session_id:
            ctx.mgr.clear_history(ctx.session_id)
        action_label = {
            ("clear", "clear"): "Всё очищено",
            ("clear", "keep"): "context очищен, Favorite.md сохранён",
            ("keep", "keep"): "Оба файла сохранены, контекст сброшен",
        }.get((ctx_action, fav_action), "Сброс применён")
        console.print(f"[bold {ORANGE}]●[/bold {ORANGE}] [dim {GRAY}]{action_label}. Контекст сброшен.[/dim {GRAY}]")
      else:
        err = apply_result.get("error", "неизвестная ошибка")
        console.print(f"[red]Ошибка: {err}[/red]")
  
      _wait()


    def _wait() -> None:
      try:
          input("\n  [Enter чтобы продолжить]")
      except (EOFError, KeyboardInterrupt):
          pass

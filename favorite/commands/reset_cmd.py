"""
favorite/commands/reset_cmd.py - /reset command.
BUG A2 FIX: local-only reset when no FavoriteAPI (OpenRouter/Qwen users).
BUG A3 FIX: visual clear after reset.
BUG HIDDEN-1 FIX: _handle_limit_hit/_wait moved to module level.
BUG HIDDEN-2 FIX: local fallback when server unreachable.
"""
import time
import requests as _req
from rich.console import Console
from .base import ICommand, CommandContext
from ..ui.theme import ORANGE, GRAY
from ..ui.chat import print_status_line

console = Console()


def _is_server_unavailable(result: dict) -> bool:
  if result.get("reset") or result.get("requires_choice"):
    return False
  err = result.get("error", "")
  return "nedostupen" in err or "Cloudflare" in err or "tunnel" in err.lower()


def _try_refresh_url(cfg) -> bool:
  if not cfg.has_tg_bridge():
    return False
  from ..bridge.tg_url import fetch_url, invalidate
  print_status_line("TG Bridge", "looking for new URL...", color="#666666")
  invalidate()
  fresh_url = fetch_url(cfg.tg_bridge_token, cfg.tg_bridge_chat_id)
  current_url = cfg.favorite_api_base_url
  if fresh_url and fresh_url != current_url:
    cfg.set_favorite_api_base_url(fresh_url)
    print_status_line("TG Bridge", f"new URL: {fresh_url}", color="#ff8c00")
    return True
  print_status_line("TG Bridge", "no new URL found", color="#666666")
  return False


def _do_visual_clear(ctx: CommandContext) -> None:
  """BUG A3 FIX: clear screen + redraw banner + last 10 history entries."""
  try:
    from ..ui.welcome import clear_screen, render_welcome
    from ..config.loader import get_config as _gc
    _cfg = _gc()
    try:
      from ..agent.model_router import RouterModule as _RM
      _model = _RM.select_model("", _cfg)[1]
    except Exception:
      _model = "unknown"
    clear_screen()
    render_welcome(model_name=_model, workdir=getattr(ctx, "workdir", "."))
    if ctx.mgr and ctx.session_id:
      from rich.markup import escape as _esc
      from ..ui.chat import print_separator, print_agent_message
      h = ctx.mgr.load_history(ctx.session_id)
      if h:
        print_separator()
        for entry in h[-10:]:
          role = entry.get("type", "")
          msg = (entry.get("content") or "").strip()
          if not msg:
            continue
          if role == "user":
            console.print(f"[bold #ffffff]>[/bold #ffffff] {_esc(msg[:120])}")
          elif role in ("agent", "assistant"):
            print_agent_message(msg)
        print_separator()
    console.print("[dim]Type a message or / for commands. Ctrl+C to exit.[/dim]\n")
  except Exception:
    pass


def _wait() -> None:
  try:
    input("\n  [Enter to continue]")
  except (EOFError, KeyboardInterrupt):
    pass


def _handle_limit_hit(client, result: dict, ctx: CommandContext) -> None:
  """Context limit hit - ask what to keep. Module-level (BUG HIDDEN-1 FIX)."""
  files = result.get("files", {})
  ctx_info = files.get("context", {})
  fav_info = files.get("favorite", {})
  console.print(f"\n[bold red]Context limit (~180KB).[/bold red] Choose what to keep:\n")
  if ctx_info.get("exists"):
    size = ctx_info.get("size_chars", 0)
    preview = (ctx_info.get("preview") or "")[:80]
    console.print(f"  [bold {ORANGE}]context.md[/bold {ORANGE}] ({size} chars)")
    if preview:
      console.print(f"  [dim]  {preview}...[/dim]")
  else:
    console.print("  [dim]context.md - empty[/dim]")
  if fav_info.get("exists"):
    size = fav_info.get("size_chars", 0)
    preview = (fav_info.get("preview") or "")[:80]
    console.print(f"  [bold {ORANGE}]Favorite.md[/bold {ORANGE}] ({size} chars)")
    if preview:
      console.print(f"  [dim]  {preview}...[/dim]")
  else:
    console.print("  [dim]Favorite.md - empty[/dim]")
  console.print("\n  [bold]1.[/bold] Clear everything")
  console.print("  [bold]2.[/bold] Keep Favorite.md, clear context")
  console.print("  [bold]3.[/bold] Keep both")
  console.print("  [bold]4.[/bold] Cancel\n")
  while True:
    try:
      choice = input("  Choose [1-4]: ").strip()
    except (EOFError, KeyboardInterrupt):
      console.print("[dim]Cancelled.[/dim]")
      return
    if choice == "1":
      ctx_action, fav_action = "clear", "clear"; break
    elif choice == "2":
      ctx_action, fav_action = "clear", "keep"; break
    elif choice == "3":
      ctx_action, fav_action = "keep", "keep"; break
    elif choice == "4":
      console.print("[dim]Cancelled.[/dim]"); return
    else:
      console.print("  [dim]Enter 1, 2, 3, or 4[/dim]")
  try:
    apply_result = client.reset_context_apply(context=ctx_action, favorite=fav_action)
  except Exception as e:
    console.print(f"[red]Error applying reset: {e}[/red]")
    _wait(); return
  if apply_result.get("reset"):
    if ctx.mgr and ctx.session_id:
      ctx.mgr.clear_history(ctx.session_id)
    time.sleep(0.3)
    _do_visual_clear(ctx)
  else:
    err = apply_result.get("error", "unknown error")
    console.print(f"[red]Error: {err}[/red]")
    _wait()


class ResetCommand(ICommand):
  name = "/reset"
  description = "Reset dialog context (clear history)"
  priority = 25

  def execute(self, args: str, ctx: CommandContext) -> None:
    cfg = ctx.config
    fav_key = cfg.default_favorite_key()
    if not fav_key:
      console.print(f"\n[bold {ORANGE}]Resetting context...[/bold {ORANGE}]")
      if ctx.mgr and ctx.session_id:
        ctx.mgr.clear_history(ctx.session_id)
      console.print(f"[dim {GRAY}]Context cleared locally.[/dim {GRAY}]")
      time.sleep(0.4)
      _do_visual_clear(ctx)
      return
    from ..api.favorite_api import FavoriteApiClient
    def _make_client():
      base_url = getattr(cfg, "favorite_api_base_url", FavoriteApiClient.DEFAULT_BASE)
      return FavoriteApiClient(
        api_key=fav_key.get("key", ""),
        base_url=base_url,
        model=fav_key.get("model"),
      )
    console.print(f"\n[bold {ORANGE}]Resetting context...[/bold {ORANGE}]")
    try:
      result = _make_client().reset_context()
    except _req.exceptions.ConnectionError:
      result = None
    except Exception as e:
      console.print(f"[red]Connection error: {e}[/red]")
      if ctx.mgr and ctx.session_id:
        ctx.mgr.clear_history(ctx.session_id)
      console.print(f"[dim {GRAY}]Cleared locally (server unreachable).[/dim {GRAY}]")
      time.sleep(0.4)
      _do_visual_clear(ctx)
      return
    if result is None or _is_server_unavailable(result):
      refreshed = _try_refresh_url(cfg)
      if refreshed:
        try:
          result = _make_client().reset_context()
        except _req.exceptions.ConnectionError:
          result = None
        except Exception as e:
          console.print(f"[red]Connection error: {e}[/red]")
          if ctx.mgr and ctx.session_id:
            ctx.mgr.clear_history(ctx.session_id)
          time.sleep(0.4)
          _do_visual_clear(ctx)
          return
      if result is None or _is_server_unavailable(result):
        if ctx.mgr and ctx.session_id:
          ctx.mgr.clear_history(ctx.session_id)
        console.print(f"[dim {GRAY}]Server down - cleared locally.[/dim {GRAY}]")
        time.sleep(0.4)
        _do_visual_clear(ctx)
        return
    if result.get("requires_choice"):
      _handle_limit_hit(_make_client(), result, ctx)
      return
    if result.get("reset"):
      if ctx.mgr and ctx.session_id:
        ctx.mgr.clear_history(ctx.session_id)
      console.print(f"[dim {GRAY}]Context reset. History cleared.[/dim {GRAY}]")
      time.sleep(0.3)
      _do_visual_clear(ctx)
    else:
      err = result.get("error", "unknown error")
      console.print(f"[red]Failed to reset: {err}[/red]")
      _wait()

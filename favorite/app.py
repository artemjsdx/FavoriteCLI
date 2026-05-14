"""
FavoriteCLI — main application entry point (DI container + run loop).
"""
import os
import re
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from .platform import detect_platform
from .config.loader import get_config, reload_config
from .ui.welcome import render_welcome, clear_screen
from .ui.chat import print_agent_message, print_separator, print_status_line, reset_cmd_display
from .ui.prompt import build_session, get_prompt_tokens
from .ui.theme import STYLE
from .sessions.manager import SessionManager
from .commands.registry import CommandRegistry
from .commands.favorite_api import FavoriteApiCommand
from .commands.openrouter_api import OpenRouterApiCommand
from .commands.models import ModelsCommand
from .commands.sessions_cmd import NewSessionCommand, SessionCommand
from .commands.skills_cmd import SkillsCommand
from .commands.plan_cmd import PlanCommand
from .commands.build_cmd import BuildCommand
from .commands.agents_cmd import AgentsCommand
from .commands.memory_cmd import MemoryCommand
from .commands.tasks_cmd import TasksCommand
from .commands.usage_cmd import UsageCommand
from .commands.doctor_cmd import DoctorCommand
from .commands.recap_cmd import RecapCommand
from .commands.compact_cmd import CompactCommand
from .commands.reset_cmd import ResetCommand
from .commands.silent_cmd import SilentCommand
from .commands.auto_cmd import AutoCommand
from .commands.effort_cmd import EffortCommand
from .commands.map_cmd import MapCommand
from .commands.architect_cmd import ArchitectCommand
from .commands.telegram_cmd import TelegramCommand
from .commands.help_cmd import HelpCommand
from .commands.publish_cmd import PublishCommand
from .commands.tour_cmd import TourCommand
from .commands.web_cmd import WebCommand, FetchCommand
from .commands.modules_cmd import ModulesCommand
from .commands.snapshot_cmd import SnapshotCommand, RollbackCommand
from .commands.logs_cmd import LogsCommand
from .commands.userprompt_cmd import UserPromptCommand
from .commands.export_cmd import ExportCommand
from .commands.sandbox_cmd import SandboxCommand
from .commands.wait_cmd import WaitCommand
from .commands.import_cmd import ImportCommand
from .commands.voice_cmd import VoiceCommand
from .commands.prompt_audit_cmd import PromptAuditCommand
from .commands.stop_cmd import StopCommand
from .commands.skill_search_cmd import SkillSearchCommand
from .commands.workers_cmd import WorkersCommand
from .commands.device_cmd import DeviceCommand
from .commands.ide_cmd import IdeCommand
from .commands.model_router_cmd import ModelRouterCommand
from .commands.parallel_auto_cmd import ParallelAutoCommand
from .commands.subs_cmd import SubsCommand
from .commands.mcp_cmd import McpCommand
from .commands.mode_cmd import ModeCommand, LiteCommand, ProCommand, MaxCommand
from .skills.telegram_notify import TelegramNotifier
from .commands.base import CommandContext
from .agent.system_prompt import build_system_prompt

console = Console()

# Auto-discover and register skills at import time
try:
    from .skills.registry import SkillRegistry as _SR
    _SR.autodiscover()
except Exception:
    pass


def estimate_tokens(text: str) -> int:
  if not text: return 0
  cyr = len(re.findall(r"[Ѐ-ӿ]", text))
  rest = len(text) - cyr
  return max(1, round(cyr / 2 + rest / 4))


def _get_model_name(cfg) -> str:
  import json
  try:
      ua_file = Path(__file__).resolve().parent.parent / "config" / "user_agents.json"
      if ua_file.exists():
          ua = json.loads(ua_file.read_text(encoding="utf-8"))
          main_model = ua.get("main", {}).get("model")
          if main_model:
              return main_model.split("/")[-1]
  except Exception:
      pass
  or_key = cfg.default_openrouter_key()
  name = (or_key or {}).get("model", None)
  if not name:
      fav = cfg.default_favorite_key()
      name = ("FavoriteAPI/" + (fav.get("model") or "gemini")) if fav else "нет ключей"
  return name


def _pick_workdir() -> str:
  home = str(Path.home()); cwd = os.getcwd()
  console.print(
      "\n[bold #ff8c00]Выбери рабочую директорию:[/bold #ff8c00]\n"
      f"  [1] Текущая директория  [dim]({cwd})[/dim]\n"
      "  [2] Указать путь\n"
      f"  [3] Домашняя директория [dim]({home})[/dim]\n"
  )
  while True:
      try: choice = input("  Выбери [1/2/3]: ").strip()
      except (EOFError, KeyboardInterrupt): return cwd
      if choice == "1": return cwd
      if choice == "3": return home
      if choice == "2":
          while True:
              try: p = input("  Путь: ").strip()
              except (EOFError, KeyboardInterrupt): return cwd
              expanded = str(Path(p).expanduser())
              if Path(expanded).is_dir(): return str(Path(expanded).resolve())
              console.print(f"  [red]Не найдено: {p}[/red]")


def _build_registry() -> CommandRegistry:
  reg = CommandRegistry()
  # Navigation / help
  reg.register(HelpCommand())
  reg.register(StopCommand())
  # API keys
  reg.register(FavoriteApiCommand())
  reg.register(OpenRouterApiCommand())
  # Models / agents / sessions
  reg.register(ModelsCommand())
  reg.register(NewSessionCommand())
  reg.register(SessionCommand())
  reg.register(AgentsCommand())
  # Memory / tasks
  reg.register(MemoryCommand())
  reg.register(TasksCommand())
  # Modes
  reg.register(PlanCommand())
  reg.register(BuildCommand())
  reg.register(AutoCommand())
  reg.register(SilentCommand())
  reg.register(ModeCommand())
  reg.register(LiteCommand())
  reg.register(ProCommand())
  reg.register(MaxCommand())
  # Skills
  reg.register(SkillsCommand())
  reg.register(SkillSearchCommand())
  # Web
  reg.register(WebCommand())
  reg.register(FetchCommand())
  # Modules
  reg.register(ModulesCommand())
  # Session tools
  reg.register(SnapshotCommand())
  reg.register(RollbackCommand())
  reg.register(LogsCommand())
  reg.register(ExportCommand())
  reg.register(ImportCommand())
  reg.register(WaitCommand())
  reg.register(SandboxCommand())
  reg.register(VoiceCommand())
  reg.register(PromptAuditCommand())
    # User customisation
  reg.register(UserPromptCommand())
  reg.register(PublishCommand())
  reg.register(TourCommand())
  reg.register(EffortCommand())
  reg.register(MapCommand())
  reg.register(ArchitectCommand())
  reg.register(TelegramCommand())
  # Stats / maintenance
  reg.register(UsageCommand())
  reg.register(DoctorCommand())
  reg.register(RecapCommand())
  reg.register(CompactCommand())
  reg.register(ResetCommand())
  reg.register(WorkersCommand())
  reg.register(DeviceCommand())
  reg.register(IdeCommand())
  reg.register(ModelRouterCommand())
  reg.register(ParallelAutoCommand())
  reg.register(SubsCommand())
  reg.register(McpCommand())
  return reg


def _show_context_indicator(mgr, session_id: str) -> None:
    """§3.6 — Show ctx │ M1: XX% indicator in header."""
    try:
        from .token_usage import estimate_tokens
        history = mgr.load_history(session_id)
        total_chars = sum(len(str(e.get("content", ""))) for e in history)
        total_tokens = estimate_tokens(" " * total_chars)
        ctx_limit = 128_000
        pct = min(100, int(total_tokens * 100 / ctx_limit))
        color = "#5fd7af" if pct < 50 else "#ffaf5f" if pct < 75 else "#ff5f5f"
        console.print(
            f"  [dim #555555]ctx │ [/dim #555555][{color}]M1: {pct}%[/{color}]"
            f"  [dim #333333]{total_tokens:,} tok[/dim #333333]"
        )
    except Exception:
        pass


def _check_onboarding(workdir: str) -> None:
    """Show quick-start tips on first run."""
    try:
        flag = Path(workdir) / ".favorite_onboarded"
        if flag.exists():
            return
        console.print()
        console.print("  [bold #ff8c00]╭─ Добро пожаловать в FavoriteCLI ──────────────────╮[/bold #ff8c00]")
        console.print("  [bold #ff8c00]│[/bold #ff8c00]  Быстрый старт:")
        console.print("  [bold #ff8c00]│[/bold #ff8c00]  • Добавь API-ключ: [bold]/OpenRouter API[/bold] или [bold]/Favorite API[/bold]")
        console.print("  [bold #ff8c00]│[/bold #ff8c00]  • Создай агентов: [bold]/agents[/bold]  (Ctrl+1..9 — переключение)")
        console.print("  [bold #ff8c00]│[/bold #ff8c00]  • END — отправить  ESC — очистить  Ctrl+S — черновик")
        console.print("  [bold #ff8c00]╰────────────────────────────────────────────────────╯[/bold #ff8c00]")
        console.print()
        flag.touch()
    except Exception:
        pass


def _inject_continuity(messages: list[dict], mgr, session_id: str) -> list[dict]:
    """§25 — Prepend open-tasks reminder when history starts fresh."""
    try:
        history = mgr.load_history(session_id)
        if len(history) > 2:
            return messages
        from .tasks.manager import TaskManager
        tm = TaskManager(session_id=session_id)
        open_tasks = [t for t in tm.list_tasks() if t.get("status") not in ("done", "cancelled")]
        if not open_tasks:
            return messages
        task_lines = "\n".join(
            f"  - [{t.get('id', '?')}] {t.get('title', '?')}" for t in open_tasks[:5]
        )
        reminder = (
            f"[CONTINUITY] Незакрытых задач из предыдущего сеанса: {len(open_tasks)}\n"
            f"{task_lines}\n"
            "Продолжи работу или уточни у пользователя."
        )
        result = []
        inserted = False
        for m in messages:
            result.append(m)
            if not inserted and m.get("role") == "system":
                result.append({"role": "system", "content": reminder})
                inserted = True
        return result
    except Exception:
        return messages


def _maybe_compact(messages: list[dict], mgr, session_id: str, workdir: str, cfg) -> list[dict]:
    """§3.2 — Auto-compact at 70% context threshold."""
    try:
        from .agent.compaction import should_compact, compact_messages
        if should_compact(messages):
            print_status_line("COMPACT", "Автосжатие контекста (порог 70%)…", color="#888888")
            messages = compact_messages(messages, session_id, workdir, cfg=cfg)
            print_status_line("COMPACT", "✓ готово", color="#5fd7af")
    except Exception:
        pass
    return messages


def _maybe_reincarnate(messages: list[dict]) -> list[dict]:
    """§3.3 — Hard-reset at 75% context (after compaction failed to help)."""
    try:
        from .token_usage import estimate_tokens
        total = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
        if total > 96_000:  # 75% of 128k
            print_status_line("REINCARNATE", "Контекст критичен — сброс до 6 последних сообщений…", color="#ffaf5f")
            sys_msgs = [m for m in messages if m.get("role") == "system"]
            recent   = [m for m in messages if m.get("role") != "system"][-6:]
            notice   = {"role": "system", "content": "[REINCARNATION] Context reset — continuing from last 6 messages only."}
            messages = sys_msgs + [notice] + recent
            print_status_line("REINCARNATE", "✓ реинкарнация выполнена", color="#5fd7af")
    except Exception:
        pass
    return messages


def _show_home(workdir: str, mgr=None, session_id: str = None) -> None:
    cfg = reload_config()
    model_name = _get_model_name(cfg)
    clear_screen()
    render_welcome(model_name=model_name, workdir=workdir)
    if mgr and session_id:
        _show_context_indicator(mgr, session_id)
    if not cfg.has_any_provider():
        console.print(
            "  [dim]Ключи не настроены. Добавь через [/dim]"
            "[bold #ff8c00]/OpenRouter API[/bold #ff8c00]"
            "[dim] или [/dim]"
            "[bold #ff8c00]/Favorite API[/bold #ff8c00]\n"
        )
    console.print("[dim]Введи сообщение или / для команд. Ctrl+C — выход.[/dim]\n")




def _restore_chat(mgr: SessionManager, session_id: str, workdir: str) -> None:
    """После выхода из команды восстанавливает историю чата без очистки экрана."""
    from rich.markup import escape as _esc
    history = mgr.load_history(session_id)
    if history:
        print_separator()
        for entry in history[-20:]:
            role = entry.get("type", "")
            msg = (entry.get("content") or "").strip()
            if not msg:
                continue
            if role == "user":
                console.print(f"[bold #ffffff]>[/bold #ffffff] {_esc(msg[:200])}")
            elif role in ("agent", "assistant"):
                print_agent_message(msg)
        print_separator()
    cfg = reload_config()
    if not cfg.has_any_provider():
        console.print(
            "  [dim]Ключи не настроены. Добавь через [/dim]"
            "[bold #ff8c00]/OpenRouter API[/bold #ff8c00]"
            "[dim] или [/dim]"
            "[bold #ff8c00]/Favorite API[/bold #ff8c00]\n"
        )
    console.print("[dim]Введи сообщение или / для команд. Ctrl+C — выход.[/dim]\n")

def _load_system_prompt(cfg, workdir: str, session_id: str = None, mode: str = "chat") -> str:
  try: return build_system_prompt(cfg, workdir, session_id=session_id, mode=mode)
  except Exception as e:
      console.print(f"[red]Ошибка загрузки системного промпта: {e}[/red]"); return ""


def _build_messages(text: str, history: list[dict], system_prompt: str) -> list[dict]:
  messages: list[dict] = []
  if system_prompt:
      messages.append({"role": "system", "content": system_prompt})
  for entry in history[-20:]:
      role = entry.get("type", ""); content = entry.get("content", "")
      if role == "user": messages.append({"role": "user", "content": content})
      elif role in ("agent", "assistant"): messages.append({"role": "assistant", "content": content})
  messages.append({"role": "user", "content": text})
  return messages


def _show_tokens_from_text(session_id: str, mgr: SessionManager, text: str) -> None:
  tokens = estimate_tokens(text)
  mgr.update_stats(session_id, tokens)
  print_status_line("tokens", f"~{tokens:,}", color="#444444")


def _save_session_txt(mgr: SessionManager, session_id: str, ctx) -> None:
  from datetime import datetime
  history = mgr.load_history(session_id)
  if not history: console.print("\n  [dim]Сессия пуста — нечего сохранять.[/dim]"); return
  lines = []
  for e in history:
      role = e.get("type",""); content = (e.get("content") or "").strip()
      if not content: continue
      if role == "user": lines.append(f"❯ {content}")
      elif role in ("agent","assistant"): lines.append(f"● {content}")
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  out = Path(ctx.workdir) / f"session_{ts}.txt"
  out.write_text("\n\n".join(lines), encoding="utf-8")
  console.print(f"\n  [green]✓ Сохранено:[/green] {out}")


def run() -> None:
  from .memory.hot_reload import start_watcher
  from .memory.favorite_md import _DEFAULT as FAV_MD_PATH

  platform = detect_platform()
  workdir = _pick_workdir()
  mgr = SessionManager()
  session_id = mgr.create_session(workdir=workdir)
  registry = _build_registry()
  _telegram = TelegramNotifier("config/telegram.json")
  ctx = CommandContext(
      workdir=workdir, session_id=session_id, platform=platform,
      config=get_config(), mgr=mgr, registry=registry,
  )
  # §PATCH-1: cache current mode on startup
  try:
      import json as _j; _mf2 = Path(__file__).resolve().parent.parent / "config" / "mode.json"
      ctx.current_mode = _j.loads(_mf2.read_text(encoding="utf-8")).get("mode", "pro") if _mf2.exists() else "pro"
  except Exception:
      ctx.current_mode = "pro"

  def on_fav_md_change():
      console.print("\n● [dim]Favorite.md обновлён[/dim]")

  watcher = start_watcher(str(FAV_MD_PATH), on_fav_md_change)

  # §43 — Check crashed workers on startup
  try:
      from .commands.workers_cmd import check_workers_on_startup
      _crashed = check_workers_on_startup()
      for _w in _crashed:
          console.print(f"  [red]⚠ Воркер упал:[/red] [dim]{_w.get('id','?')}: {_w.get('name','?')}[/dim]")
          console.print(f"  [dim]  /workers logs {_w.get('id','?')}[/dim]")
  except Exception:
      pass

  # §39.2 — Check for unsaved draft on startup
  try:
      from .draft import check_draft_on_startup, clear_draft
      _saved_draft = check_draft_on_startup()
      if _saved_draft:
          _preview = _saved_draft[:40] + ("..." if len(_saved_draft) > 40 else "")
          console.print(f"  [bold #f97316]╭─ Черновик ─────────────────────────────────╮[/bold #f97316]")
          console.print(f"  [bold #f97316]│[/bold #f97316]  «{_preview}»")
          console.print(f"  [bold #f97316]│[/bold #f97316]  [1] Восстановить  [2] Удалить")
          console.print(f"  [bold #f97316]╰────────────────────────────────────────────╯[/bold #f97316]")
          _choice = input("  Выбор: ").strip()
          if _choice == "2":
              clear_draft()
          elif _choice == "1":
              ctx.draft_text = _saved_draft
  except Exception:
      pass

  # Fire on_session_start hooks
  try:
      from .skills.hooks_skill import fire_hooks
      fire_hooks("on_session_start", ctx=ctx)
  except Exception:
      pass

  def on_export():
      _save_session_txt(mgr, session_id, ctx)

  session = build_session(on_export=on_export)
  _show_home(workdir, mgr=mgr, session_id=session_id)
  _check_onboarding(workdir)

  _MODE_COLORS = {"lite": "#4a9eff", "pro": "#ff8c00", "max": "#ff3333"}
  _MODE_LABELS = {"lite": "LITE", "pro": "PRO", "max": "MAX"}

  def _current_prompt():
      auto = getattr(ctx, "auto_mode", False)
      plan = getattr(ctx, "plan_mode", False)
      # §PATCH-1: read from ctx attribute, updated by mode_cmd
      _mode = getattr(ctx, "current_mode", "pro")
      _color = _MODE_COLORS.get(_mode, "#ff8c00")
      _label = _MODE_LABELS.get(_mode, "PRO")
      _mode_token = (f"fg:{_color} bold", f"[{_label}] ")

      if auto and plan:
          return [_mode_token, ("fg:#ff8c00 bold", "[AUTO+ПЛАН] "), ("class:prompt-arrow", "❯ ")]
      if auto:
          return [_mode_token, ("fg:#ff8c00 bold", "[AUTO] "), ("class:prompt-arrow", "❯ ")]
      if plan:
          return [_mode_token, ("fg:#ff8c00 bold", "[ПЛАН] "), ("class:prompt-arrow", "❯ ")]
      return [_mode_token, ("class:prompt-arrow", "❯ ")]

  # §39.2 — Ctrl+S saves draft via key binding on PromptSession
  try:
      from prompt_toolkit.keys import Keys
      from prompt_toolkit.filters import Condition
      @session.app.key_bindings.add("c-s")
      def _ctrl_s_draft(event):
          """Ctrl+S — save current input as draft."""
          text = event.app.current_buffer.text
          if text.strip():
              try:
                  from .draft import save_draft
                  save_draft(text)
                  event.app.current_buffer.set_document(
                      event.app.current_buffer.document, bypass_readonly=False
                  )
              except Exception:
                  pass
  except Exception:
      pass

  try:
      while True:
          try: raw = session.prompt(_current_prompt, style=STYLE)
          except KeyboardInterrupt:
              console.print("\n[dim]Ctrl+C — нажми ещё раз для выхода.[/dim]")
              try: session.prompt([("class:prompt-arrow", " ")], style=STYLE)
              except (KeyboardInterrupt, EOFError): break
              continue
          except EOFError:
              try:
                  from .skills.hooks_skill import fire_hooks as _fh
                  _fh("on_session_end", ctx=ctx)
              except Exception:
                  pass
              break

          raw = raw.strip()
          if not raw: continue

          # §39.1 — Direct bash prefix "!"
          if raw.startswith("!"):
              _cmd = raw[1:].strip()
              if _cmd:
                  import subprocess as _sub_bang
                  from .ui.chat import print_shell_cmd as _psc_bang, print_shell_output as _pso_bang
                  _psc_bang(_cmd)
                  try:
                      _r = _sub_bang.run(_cmd, shell=True, cwd=ctx.workdir,
                                         capture_output=True, text=True, timeout=60)
                      _out = (_r.stdout or "").strip(); _err = (_r.stderr or "").strip()
                      _pso_bang(_out, _err)
                      # Log to auto.log
                      try:
                          from .commands.logs_cmd import log_event
                          log_event(ctx.workdir, ctx.session_id, "DIRECT_SHELL", _cmd[:80])
                      except Exception:
                          pass
                  except _sub_bang.TimeoutExpired:
                      console.print("  [red]TIMEOUT (60s)[/red]")
                  except Exception as _e_bang:
                      console.print(f"  [red]ERROR: {_e_bang}[/red]")
              continue

          if raw.startswith("/"):
            matched_cmd = None; matched_args = ""
            for c in registry.all_sorted():
                if raw.lower().startswith(c.name.lower()):
                    matched_cmd = c; matched_args = raw[len(c.name):].strip(); break
            if matched_cmd:
                try: matched_cmd.execute(matched_args, ctx)
                except Exception as e: console.print(f"[red]Ошибка команды: {e}[/red]")
                _restore_chat(mgr, session_id, workdir)
            else: console.print(f"[dim]Команда не найдена: {raw}[/dim]")
          else:
              mgr.append_history(session_id, {"type": "user", "content": raw})
              cfg = reload_config()
              if not cfg.has_any_provider():
                  console.print(
                      "[yellow]Нет API-ключа.[/yellow] "
                      "Добавь через [bold #ff8c00]/OpenRouter API[/bold #ff8c00]"
                  )
              else:
                  history = mgr.load_history(session_id)
                  _mode = "auto" if getattr(ctx, "auto_mode", False) else "chat"
                  system_prompt = _load_system_prompt(cfg, ctx.workdir, session_id=session_id, mode=_mode)
                  send_text = ("[ПЛАН РЕЖИМ]\n" + raw) if getattr(ctx, "plan_mode", False) else raw
                  messages = _build_messages(send_text, history[:-1], system_prompt)
                  _handle_chat(send_text, messages, ctx, mgr, session_id, cfg)
  finally:
      watcher.stop(); watcher.join()

  clear_screen()
  console.print("\n[dim]До встречи.[/dim]\n")


def _handle_chat(text, messages, ctx, mgr, session_id, cfg) -> None:
  from .agent.llm import call_llm, stream_llm
  from .ui.spinner import Spinner
  import requests as _req

  # §25 — inject open-tasks continuity reminder when history is fresh
  messages = _inject_continuity(messages, mgr, session_id)

  # Check actual configured provider — don't assume OR just because OR key exists
  _prompt_text = messages[-1]["content"] if messages else ""
  try:
    from .agent.model_router import RouterModule as _RM
    _active_provider, _, _ = _RM.select_model(_prompt_text, cfg)
  except Exception:
    _active_provider = "OpenRouter"

  or_key = cfg.default_openrouter_key()

  if or_key and _active_provider == "OpenRouter":
      full = ""
      try:
          from .ui.chat import StatusSpinner as _StatusSpinner
          _spin_or = _StatusSpinner("Thinking")
          _spin_or.start()
          for chunk in stream_llm(messages, cfg):
              full += chunk
          _spin_or.stop()
      except KeyboardInterrupt:
          console.print("\n[dim](прервано)[/dim]")
          if full:
              all_text = _agent_loop(full, messages, ctx, mgr, session_id, cfg, skip_first_print=True)
              _show_tokens_from_text(session_id, mgr, full + (all_text or ""))
          return
      except _req.exceptions.ConnectionError:
          console.print(f"\n[bold red]Не удалось подключиться к OpenRouter.[/bold red] Пробую FavoriteAPI...")
      except _req.exceptions.HTTPError as http_err:
          status = getattr(getattr(http_err,"response",None),"status_code",None)
          if status == 401:
              console.print("\n[red]OpenRouter: ключ не авторизован (401).[/red]")
          else: console.print(f"\n[red]Ошибка API: {http_err}[/red]")
          return
      except Exception as e:
          console.print(f"\n[red]Ошибка API: {e}[/red]"); return
      else:
          if full.strip():
              all_text = _agent_loop(full, messages, ctx, mgr, session_id, cfg, skip_first_print=False)
              _show_tokens_from_text(session_id, mgr, full + (all_text or ""))
          return

  spinner = Spinner("Thinking"); spinner.start()
  try: response = call_llm(messages, cfg)
  except (_req.exceptions.ConnectionError, _req.exceptions.HTTPError) as net_err:
      spinner.stop()
      current_url = cfg.favorite_api_base_url
      if cfg.has_tg_bridge():
          print_status_line("TG Bridge", "ищу новый URL...", color="#666666")
          from .bridge.tg_url import fetch_url, invalidate; invalidate()
          fresh_url = fetch_url(cfg.tg_bridge_token, cfg.tg_bridge_chat_id)
          if fresh_url and fresh_url != current_url:
              cfg.set_favorite_api_base_url(fresh_url)
              print_status_line("TG Bridge", f"новый URL: {fresh_url}", color="#ff8c00")
              spin2 = Spinner("Thinking"); spin2.start()
              try:
                  response = call_llm(messages, cfg); spin2.stop()
                  all_text = _agent_loop(response, messages, ctx, mgr, session_id, cfg)
                  _show_tokens_from_text(session_id, mgr, response + (all_text or ""))
                  return
              except Exception: spin2.stop()
      console.print(f"[bold red]Не удалось подключиться к FavoriteAPI.[/bold red] [dim]{current_url}[/dim]")
      try:
          new_url = input("  URL: ").strip()
          if new_url:
              if not new_url.startswith("http"): new_url = "http://" + new_url
              cfg.set_favorite_api_base_url(new_url)
              console.print(f"[green]Сохранено:[/green] {new_url}. Повтори сообщение.")
      except (EOFError, KeyboardInterrupt): pass
      return
  except Exception as e: spinner.stop(); console.print(f"[red]Ошибка API: {e}[/red]"); return
  spinner.stop()
  if response:
      all_text = _agent_loop(response, messages, ctx, mgr, session_id, cfg)
      _show_tokens_from_text(session_id, mgr, response + (all_text or ""))


def _run_auto_critic(messages: list[dict], cfg) -> str:
    """
    Критик-агент: проверяет работу гл. агента. Возвращает "APPROVED" или описание замечаний.
    """
    from .agent.llm import call_llm
    critic_system = (
        "You are a strict quality critic agent in AUTO mode.\n"
        "Review what the main agent has done and decide if the user's request is fully satisfied.\n\n"
        "Rules:\n"
        "1. If ALL requirements are met and work is complete: respond with exactly APPROVED\n"
        "2. If anything is missing or broken: describe in Russian what needs fixing (1-4 sentences)\n"
        "3. APPROVED means you are 100% confident the task is done. Nothing less."
    )
    parts: list[str] = []
    for msg in messages[-40:]:
        role = msg.get("role", "")
        txt = (msg.get("content") or "").strip()
        if len(txt) > 700: txt = txt[:700] + "...[cut]"
        if role == "user": parts.append(f"USER: {txt}")
        elif role == "assistant": parts.append(f"AGENT: {txt}")
    critic_msgs = [
        {"role": "system", "content": critic_system},
        {"role": "user", "content": "Оцени работу агента:\n\n" + "\n\n".join(parts)},
    ]
    try:
        return call_llm(critic_msgs, cfg).strip()
    except Exception:
        return "APPROVED"


def _agent_loop(first_response, messages, ctx, mgr, session_id, cfg, skip_first_print=False) -> str:
    from .agent.tags import extract_tags, strip_tags
    from .agent.executor import execute_tags_with_output
    from .agent.llm import call_llm
    from .ui.spinner import Spinner

    all_responses: list[str] = []
    response = first_response; step = 0
    compact_requested = False

    while True:
        tags = extract_tags(response)
        clean = strip_tags(response) if tags else response
        if clean.strip() and not (step == 0 and skip_first_print):
              if not getattr(ctx, "silent_this_turn", False):
                  print_agent_message(clean)
              setattr(ctx, "silent_this_turn", False)  # reset after each turn
        all_responses.append(response); step += 1

        if not tags:
            if getattr(ctx, "auto_mode", False):
                from .ui.chat import print_status_line as _psl
                _psl("AUTO", "проверяю результат через критика...", color="#666666")
                critic_verdict = _run_auto_critic(
                    messages + [{"role": "assistant", "content": response}], cfg
                )
                if "APPROVED" in critic_verdict.upper()[:20]:
                    _psl("AUTO", "✓ критик одобрил — задача завершена", color="#ff8c00")
                    break
                else:
                    _psl("AUTO", "критик нашёл замечания — продолжаю", color="#666666")
                    print_agent_message(f"**[Критик]:** {critic_verdict}")
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": (
                        f"[ПРОВЕРКА КРИТИКА]\n{critic_verdict}\n\n"
                        "Устрани замечания и продолжи работу. "
                        "Когда всё будет готово — дай итоговый ответ без тегов действий."
                    )})
                    spinner2 = Spinner("Thinking"); spinner2.start()
                    try: response = call_llm(messages, cfg); spinner2.stop()
                    except KeyboardInterrupt: spinner2.stop(); console.print("\n[dim](прервано)[/dim]"); break
                    except Exception as e2: spinner2.stop(); console.print(f"[red]Ошибка API: {e2}[/red]"); break
                    continue
            break

        tool_output = execute_tags_with_output(tags, ctx, cfg)
        _ACTION_TAGS = {"SHELL_RAW", "SHELL_BG", "SKILL", "CONTINUE", "POLL",
                        "SUB_AGENT", "READ_FILE", "WRITE_FILE", "ASK_USER", "NEXT"}
        has_actions = any(t.name.upper() in _ACTION_TAGS for t in tags)
        
        # Check for WRITE_CTX to handle compaction completion
        if any(t.name.upper() == "WRITE_CTX" for t in tags) and compact_requested:
            try:
                summary_file = Path(ctx.workdir) / "sessions" / session_id / "context_summary.md"
                if summary_file.exists():
                    summary_content = summary_file.read_text(encoding="utf-8")
                    # Truncate history to last 4 messages and prepend summary
                    history = mgr.load_history(session_id)
                    new_history = [
                        {"type": "system", "content": f"[Context summary from earlier]\n{summary_content}"}
                    ] + history[-4:]
                    mgr.save_history(session_id, new_history)
                    print_status_line("Context", "Контекст сжат. История сокращена.", color="#888888")
                    compact_requested = False
            except Exception as e:
                console.print(f"  [dim red]Compaction error: {e}[/dim red]")

        # §17.1 — WAIT_USER: pause autonomous loop for human input
        if tool_output and "__WAIT_USER__" in tool_output:
            setattr(ctx, "auto_mode", False)
            console.print()
            console.print("  [bold #ff8c00]⏸ Агент ждёт тебя. Ответь и продолжай.[/bold #ff8c00]")
            break
        if not has_actions or not tool_output: break

        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"[tool output]\n{tool_output}"})

        # §3.2/§3.3 — auto-compact then reincarnate if needed
        messages = _maybe_compact(messages, mgr, session_id, ctx.workdir, cfg)
        messages = _maybe_reincarnate(messages)

        # Auto-compaction logic
        history = mgr.load_history(session_id)
        total_tokens = sum(estimate_tokens(m.get("content", "")) for m in history)
        if total_tokens > 16000 and not compact_requested:
            console.print(f"  [dim #888888]Контекст достигает предела (~{total_tokens} токенов). Прошу агента сжать контекст...[/dim #888888]")
            messages.append({
                "role": "system", 
                "content": "SYSTEM: Context is getting large. Please summarize key context in a WRITE_CTX tag now, then continue your work. Use English for the summary to save tokens."
            })
            compact_requested = True

        spinner = Spinner("Thinking"); spinner.start()
        try: response = call_llm(messages, cfg); spinner.stop()
        except KeyboardInterrupt: spinner.stop(); console.print("\n[dim](прервано)[/dim]"); break
        except Exception as e: spinner.stop(); console.print(f"[red]Ошибка API: {e}[/red]"); break

    final = "\n".join(all_responses)
    from .agent.response_processor import strip_thinking_blocks
    final = strip_thinking_blocks(final)
    mgr.append_history(session_id, {"type": "agent", "content": final})
    return "\n".join(all_responses[1:]) if len(all_responses) > 1 else ""

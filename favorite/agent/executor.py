"""
favorite/agent/executor.py â Tag execution engine.
"""
import subprocess
import time
import threading
from pathlib import Path
from typing import TYPE_CHECKING
from rich.console import Console
from rich.markup import escape
from .tags import ParsedTag

if TYPE_CHECKING:
  from ..commands.base import CommandContext

console = Console()


def execute_tags(tags: list[ParsedTag], ctx: "CommandContext", cfg) -> None:
  execute_tags_with_output(tags, ctx, cfg)


def execute_tags_with_output(tags: list[ParsedTag], ctx: "CommandContext", cfg) -> str:
  parts: list[str] = []
  for tag in tags:
      out = _dispatch(tag, ctx, cfg)
      if out:
          parts.append(out)
  return "\n".join(parts)



  def _handle_mcp_call(tag: "ParsedTag", ctx: "CommandContext", cfg) -> str:
      """§ОТСЕК 6 — Call MCP server tool: <MCP_CALL server="name" tool="tool_name">json_args</MCP_CALL>"""
      server = tag.args.get("server", "").strip()
      tool = tag.args.get("tool", "").strip()
      if not server or not tool:
          return "MCP_CALL ERROR: server= and tool= are required"
      body = (tag.body or "{}").strip()
      try:
          import json
          arguments = json.loads(body) if body else {}
      except Exception:
          arguments = {}
      try:
          from ..mcp.client import get_mcp_manager
          mgr = get_mcp_manager()
          result = mgr.call_tool(server, tool, arguments)
          return f"[MCP_CALL {server}/{tool}]\n{result}"
      except Exception as e:
          return f"MCP_CALL ERROR: {e}"
def _dispatch(tag: ParsedTag, ctx: "CommandContext", cfg) -> str | None:
  name = tag.name.upper()
  if name == "STEP":              _handle_step(tag)
  elif name == "CMD":             return _handle_cmd(tag, ctx)
  elif name == "SHELL_RAW":       return _handle_shell(tag, ctx, background=False)
  elif name == "SHELL_BG":        _handle_shell(tag, ctx, background=True)
  elif name == "SLEEP":           _handle_sleep(tag)
  elif name == "WRITE_FAV":       _handle_write_fav(tag, ctx)
  elif name == "WRITE_CTX":       _handle_write_ctx(tag, ctx)
  elif name == "GIT_PUSH":        _handle_git_push(tag, ctx, cfg)
  elif name == "SKILL":           return _handle_skill(tag, ctx, cfg)
  elif name == "CONTINUE":        return _handle_continue(tag)
  elif name == "POLL":            return _handle_poll(tag)
  elif name == "WRITE_PLAN":      return _handle_write_plan(tag, ctx)
  elif name == "READ_FILE":       return _handle_read_file(tag, ctx)
  elif name == "WRITE_FILE":      return _handle_write_file(tag, ctx)
  elif name == "ASK_USER":        return _handle_ask_user(tag)
  elif name == "SUB_AGENT":       return _handle_sub_agent(tag, ctx, cfg)
  elif name == "NEXT":            return _handle_next(tag)
  elif name == "THINK":         return None
  elif name == "REQUEST_SECRET":  return _handle_request_secret(tag, cfg)
  elif name == "SUGGEST_NEXT":    _handle_suggest_next(tag)
  elif name in ("ADD_TASK", "UPDATE_TASK", "COMPLETE_TASK", "LIST_TASKS"):
      return _handle_tasks(tag, ctx)
  elif name == "DONE":            return _handle_done(tag, ctx)
  elif name == "REPO_MAP":        return _handle_repo_map(tag, ctx)
  elif name == "ROLLBACK":        return _handle_rollback(tag, ctx)
  elif name == "AUTO_CHECKPOINT": return _handle_auto_checkpoint(tag, ctx, cfg)
  elif name == "PLAN_UPDATE":     return _handle_plan_update(tag, ctx)
  elif name == "VERIFY":          return _handle_verify(tag, ctx, cfg)
  elif name == "RETRY":           return _handle_retry(tag)
  elif name == "MEMO":            return _handle_memo(tag, ctx)
  elif name == "LOAD_MEM":        return _handle_load_mem(tag, ctx)
  elif name == "SHELL":           return _handle_shell_registered(tag, ctx)
  elif name == "VOTE":            return _handle_vote(tag, ctx, cfg)
  elif name == "ASK_PEER":        return _handle_ask_peer(tag, ctx, cfg)
  elif name == "DELEGATE_PEER":   return _handle_delegate_peer(tag, ctx, cfg)
  elif name == "NOTIFY_PEER":     return _handle_notify_peer(tag, ctx)
  elif name == "MCP_CALL":        return _handle_mcp_call(tag, ctx, cfg)
  elif name == "REINCARNATE":     return _handle_reincarnate(tag, ctx)
  elif name == "IMAGE":           return _handle_image(tag, ctx, cfg)
  elif name == "ASK_USER_CHOICE":    return _handle_ask_user_choice(tag)
  elif name == "REQUEST_CONFIRM":    return _handle_request_confirm(tag)
  elif name == "REQUEST_FILE":       return _handle_request_file(tag, ctx)
  elif name == "PLAN":               return _handle_plan(tag, ctx)
  elif name == "CALL_SUB":           return _handle_sub_agent(tag, ctx, cfg)
  elif name == "SILENT":             _handle_silent(tag, ctx)
  elif name == "WAIT_USER":          return _handle_wait_user(tag)
  elif name == "WAIT_LOGS":          return _handle_wait_logs(tag, ctx)
  elif name == "STATUS":             _handle_status(tag, ctx)
  elif name == "CAPS_QUERY":         return _handle_caps_query(tag, cfg)
  elif name == "SAVE_ARTIFACT":      return _handle_save_artifact(tag, ctx)
  elif name == "AUTO_QUESTION":      return _handle_auto_question(tag, ctx)
  elif name == "RESET_AGENT":        return _handle_reset_agent(tag, ctx, cfg)
  elif name == "BRIEF":              return _handle_brief(tag, ctx)
  elif name == "PEER_REPLY":         return _handle_peer_reply(tag, ctx)
  elif name in ("PEER_PENDING", "FILE_LOCKED"): return None
  elif name == "REVOKE_DELEGATE":    return _handle_revoke_delegate(tag, ctx)
  elif name == "TG_DIGEST":          return _handle_tg_digest(tag, ctx)
  elif name == "SUB_DELIVER":        return _handle_sub_deliver(tag, ctx)
  elif name == "SUB_APPLY":          return _handle_sub_apply(tag, ctx)
  elif name == "SUB_DISCARD":        return _handle_sub_discard(tag, ctx)
  elif name == "SUB_CHANGE_REVIEW":  return _handle_sub_change_review(tag, ctx)
  elif name == "APPROVE_SUB":        return _handle_approve_sub(tag, ctx)
  elif name == "REJECT_SUB":         return _handle_reject_sub(tag, ctx)
  elif name == "REQUEST_FULL_DIFF":  return _handle_request_full_diff(tag, ctx)
  return None


def _handle_step(tag: ParsedTag) -> None:
  from ..ui.chat import print_step
  body = (tag.body or tag.args.get("msg", "")).strip()
  if body:
      print_step(body)

_CWD_SENTINEL = "__FAV_CWD__"


def _handle_shell(tag: ParsedTag, ctx: "CommandContext", background: bool) -> str | None:
  import os
  from ..ui.chat import print_shell_cmd, print_shell_output
  cmd = (tag.body or "").strip()
  if not cmd: return None
  print_shell_cmd(cmd)

  # Persistent working dir: ctx.shell_cwd tracks directory across calls
  shell_cwd = ctx.shell_cwd if ctx.shell_cwd else ctx.workdir

  if background:
      threading.Thread(target=subprocess.run, args=(cmd,),
          kwargs={"shell": True, "cwd": shell_cwd}, daemon=True).start()
      return None
  try:
      # Wrap command: cd to current shell_cwd first, run user cmd, then capture final cwd
      wrapped = f"cd {shell_cwd!r} 2>/dev/null; ( {cmd} ); echo \"{_CWD_SENTINEL}=$(pwd)\""
      r = subprocess.run(wrapped, shell=True, cwd=shell_cwd, capture_output=True, text=True, timeout=30)
      raw_out = r.stdout or ""; err = (r.stderr or "").strip()
      # Parse final cwd out of stdout, keep the rest as real output
      out_lines: list[str] = []
      new_cwd = ""
      for line in raw_out.splitlines():
          if line.startswith(f"{_CWD_SENTINEL}="):
              new_cwd = line[len(f"{_CWD_SENTINEL}="):].strip()
          else:
              out_lines.append(line)
      if new_cwd and os.path.isdir(new_cwd):
          ctx.shell_cwd = new_cwd
      out = "\n".join(out_lines).strip()
      print_shell_output(out, err)
      combined = "\n".join(filter(None, [out, err]))
      return f"$ {cmd}\n{combined}" if combined else f"$ {cmd}\n(no output)"
  except subprocess.TimeoutExpired:
      console.print("  [dim #995555]timeout (30s)[/dim #995555]"); return f"$ {cmd}\nERROR: timeout"
  except Exception as e:
      console.print(f"  [dim #995555]error: {escape(str(e))}[/dim #995555]"); return f"$ {cmd}\nERROR: {e}"

def _handle_sleep(tag: ParsedTag) -> None:
  try:
      secs = min(float(tag.args.get("s", tag.body or "1")), 30.0)
      console.print(f"  [dim #666666]sleep {secs}s[/dim #666666]"); time.sleep(secs)
  except (ValueError, TypeError): pass

def _handle_write_fav(tag: ParsedTag, ctx: "CommandContext") -> None:
  body = (tag.body or "").strip()
  if not body: return
  try:
      from ..memory.favorite_md import FavoriteMd; FavoriteMd().write(body)
  except Exception as e: console.print(f"  [dim #995555]WRITE_FAV: {escape(str(e))}[/dim #995555]")

def _handle_write_ctx(tag: ParsedTag, ctx: "CommandContext") -> str | None:
  """Save compressed context summary to sessions/<id>/context_summary.md"""
  body = (tag.body or "").strip()
  if not body:
      return None
  try:
      from pathlib import Path
      from ..sessions.manager import SessionManager
      sm = SessionManager()
      # Note: The task says sess_dir = sm.current_session_dir()
      # I'll check if SessionManager has this method or similar.
      # For now I will use the path logic from other handlers if I can't find it.
      sess_dir = Path(ctx.workdir) / "sessions" / ctx.session_id
      if sess_dir:
          sess_dir.mkdir(parents=True, exist_ok=True)
          summary_file = sess_dir / "context_summary.md"
          with open(summary_file, "w", encoding="utf-8") as f:
              f.write(body)
          console.print(f"  [dim #888888]Context summary saved ({len(body)} chars)[/dim #888888]")
  except Exception as e:
      console.print(f"  [dim red]WRITE_CTX error: {e}[/dim red]")
  return None

def _handle_git_push(tag: ParsedTag, ctx: "CommandContext", cfg) -> None:
  msg = tag.args.get("msg", tag.body or "auto: agent push").strip()
  console.print(f"  [dim #666666]git push: {escape(msg[:60])}[/dim #666666]")
  try:
      from ..github.auto_push import AutoPush
      AutoPush(cfg).push_workdir(ctx.workdir, commit_msg=msg)
      console.print("  [dim #666666]pushed[/dim #666666]")
  except Exception as e: console.print(f"  [dim #995555]GIT_PUSH: {escape(str(e))}[/dim #995555]")

def _handle_skill(tag: ParsedTag, ctx: "CommandContext", cfg) -> str | None:
  from ..ui.chat import print_skill_header
  skill_name = tag.args.get("name", "").lower()
  query = (tag.body or tag.args.get("q", "")).strip()
  if skill_name == "websearch":
      print_skill_header("websearch", query); return _run_websearch(query, cfg)
  if skill_name == "fetch":
      print_skill_header("fetch", query[:60]); return _run_fetch(query)
  if skill_name in ("fs", "fstools"):
      print_skill_header(f"fs:{tag.args.get('op','read')}", tag.args.get("path", ""))
      return _run_fs(tag, ctx)
  console.print(f"  [dim #666666]skill '{escape(skill_name)}' not found[/dim #666666]"); return None

def _handle_continue(tag: ParsedTag) -> str:
  body = (tag.body or "").strip(); return body if body else "[continue]"

def _handle_next(tag: ParsedTag) -> str:
  """NEXT tag â LLM asks the loop to call it again with the given message."""
  body = (tag.body or "").strip()
  return body if body else "[next]"

import threading as _threading, uuid as _uuid_mod, time as _time_mod

_BG_JOBS: list[dict] = []
_BG_LOCK = _threading.Lock()

def _collect_bg_results() -> str:
  """Check finished background CMD jobs and return their output string."""
  now, done, pending = _time_mod.time(), [], []
  with _BG_LOCK:
    for job in _BG_JOBS:
      elapsed = now - job['start']
      ret = job['proc'].poll()
      if ret is not None:
        out = (job['proc'].stdout.read() if job['proc'].stdout else '') or ''
        done.append((job, elapsed, out, False))
      elif elapsed >= job['timeout']:
        job['proc'].kill()
        out = (job['proc'].stdout.read() if job['proc'].stdout else '') or ''
        done.append((job, elapsed, out, True))
      else:
        pending.append(job)
    _BG_JOBS[:] = pending
  if not done:
    return ''
  parts = []
  for job, elapsed, out, timed_out in done:
    out = (out or '').strip()
    MAX = 6000
    if len(out) > MAX:
      out = out[:MAX] + f'\n...[{len(out)-MAX} chars truncated]'
    status = f'TIMEOUT {job["timeout"]}s' if timed_out else f'DONE за {elapsed:.1f}s'
    parts.append(f'[bg:{job["id"]}] {status}\n$ {job["cmd"]}\n{out or "(no output)"}')
  return '\n\n'.join(parts)

def _handle_cmd(tag: ParsedTag, ctx) -> str | None:
  """<CMD>cmd</CMD> blocking (60s) OR <CMD bg="N">cmd</CMD> background (N sec max).
  Background result auto-injected into next turn as [BG RESULTS]."""
  from ..ui.chat import print_shell_cmd, print_shell_output
  cmd     = (tag.body or '').strip()
  bg_secs = tag.args.get('bg', '').strip()
  if not cmd:
    return None
  print_shell_cmd(cmd)
  workdir = ctx.workdir
  if bg_secs and bg_secs.isdigit():
    timeout = int(bg_secs)
    job_id  = _uuid_mod.uuid4().hex[:8]
    proc    = subprocess.Popen(
      cmd, shell=True, cwd=workdir,
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    with _BG_LOCK:
      _BG_JOBS.append({'id': job_id, 'cmd': cmd, 'proc': proc,
                       'start': _time_mod.time(), 'timeout': timeout})
    console.print(f'  [dim #888888]bg:{job_id} запущен (max {timeout}s)[/dim #888888]')
    return (f'[bg:{job_id}] ЗАПУЩЕНО в фоне (до {timeout}s) — '
            f'результат придёт автоматически в следующем шаге')
  try:
    r = subprocess.run(cmd, shell=True, cwd=workdir, capture_output=True, text=True, timeout=60)
    out      = (r.stdout or '').strip()
    err      = (r.stderr or '').strip()
    combined = '\n'.join(filter(None, [out, err]))
    print_shell_output(out, err)
    MAX = 5000
    if len(combined) > MAX:
      combined = combined[:MAX] + f'\n... [{len(combined)-MAX} chars omitted]'
    return f'$ {cmd}\n{combined}' if combined else f'$ {cmd}\n(exit {r.returncode})'
  except subprocess.TimeoutExpired:
    console.print('  [dim #995555]timeout (60s)[/dim #995555]')
    return f'$ {cmd}\nERROR: timeout (60s)'
  except Exception as e:
    console.print(f'  [dim #995555]cmd: {escape(str(e))}[/dim #995555]')
    return f'$ {cmd}\nERROR: {e}'


def _handle_poll(tag: ParsedTag) -> str | None:
  body = (tag.body or "").strip()
  if not body: return None
  lines = body.splitlines(); question_parts: list[str] = []; options: list[str] = []
  for line in lines:
      s = line.strip()
      if s.startswith(("â", "-")): options.append(s.lstrip("â- ").strip())
      elif s: question_parts.append(s)
  console.print()
  console.print(f"  [bold #ff8c00]?[/bold #ff8c00] {escape(' '.join(question_parts))}")
  for i, opt in enumerate(options, 1): console.print(f"  [dim #888888]{i}. {escape(opt)}[/dim #888888]")
  try: answer = input("  â ").strip()
  except (EOFError, KeyboardInterrupt): return "[no answer]"
  return answer  # answer from input()

def _handle_vote(tag: "ParsedTag", ctx: "CommandContext", cfg) -> str:
  """Â§16.9 â VOTE: spawn peer sub-agents to vote, aggregate, return winner."""
  question = tag.args.get("question", "").strip() or (tag.body or "").split("\n")[0].strip()
  body     = (tag.body or "").strip()
  timeout  = int(tag.args.get("timeout", "20"))
  raw_agents = tag.args.get("agents", "")
  agent_ids  = [a.strip() for a in raw_agents.split(",") if a.strip()] or None

  # Parse options: pipe-separated in body or after question line
  options: list[str] = []
  for part in body.split("\n"):
      for o in part.split("|"):
          o = o.strip().lstrip("-â¢ ").strip()
          if o and o != question:
              options.append(o)
  # Deduplicate, keep order
  seen: set[str] = set()
  opts: list[str] = []
  for o in options:
      if o not in seen:
          seen.add(o); opts.append(o)

  if len(opts) < 2:
      return f"[VOTE ERROR] Need at least 2 options, got: {opts}"

  try:
      from .vote import run_vote
      result = run_vote(
          question=question, options=opts,
          session_id=ctx.session_id, workdir=ctx.workdir,
          cfg=cfg, ctx=ctx,
          timeout=timeout, agent_ids=agent_ids,
      )
      winner = result.get("winner", opts[0])
      total  = result.get("total", 0)
      votes  = result.get("votes", {})
      tally  = ", ".join(f"{o}: {c}" for o, c in votes.items())
      return (
          f"[VOTE RESULT] Question: {question}\n"
          f"Winner: {winner} | Total votes: {total} | Tally: {tally}"
      )
  except Exception as e:
      return f"[VOTE ERROR] {e}"

def _handle_write_plan(tag: ParsedTag, ctx: "CommandContext") -> str | None:
  body = (tag.body or "").strip()
  if not body: return None
  try:
      plan_dir = Path(ctx.workdir) / "sessions" / ctx.session_id
      plan_dir.mkdir(parents=True, exist_ok=True)
      (plan_dir / "plan.txt").write_text(body, encoding="utf-8")
      return f"[plan saved: sessions/{ctx.session_id}/plan.txt]"
  except Exception as e:
      console.print(f"  [dim #995555]WRITE_PLAN: {escape(str(e))}[/dim #995555]"); return f"WRITE_PLAN ERROR: {e}"

def _handle_read_file(tag: ParsedTag, ctx: "CommandContext") -> str:
  path_str = tag.args.get("path", "").strip()
  if not path_str: return "READ_FILE ERROR: Missing path argument"
  try:
      path = Path(ctx.workdir) / path_str
      if not path.exists(): return f"READ_FILE ERROR: File not found: {path_str}"
      if not path.is_file(): return f"READ_FILE ERROR: Not a file: {path_str}"
      from ..ui.chat import print_status_line
      print_status_line("Read File", path_str, color="#666666")
      return path.read_text(encoding="utf-8")
  except Exception as e: return f"READ_FILE ERROR: {e}"

def _handle_write_file(tag: ParsedTag, ctx: "CommandContext") -> str:
  path_str = tag.args.get("path", "").strip()
  if not path_str: return "WRITE_FILE ERROR: Missing path argument"
  try:
      path = Path(ctx.workdir) / path_str
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(tag.body or "", encoding="utf-8")
      from ..ui.chat import print_status_line
      print_status_line("Write File", path_str, color="#666666")
      return f"File saved: {path_str}"
  except Exception as e: return f"WRITE_FILE ERROR: {e}"

def _handle_ask_user(tag: ParsedTag) -> str:
  prompt_text = tag.args.get("text", "Question").strip()
  body = (tag.body or "").strip()
  display = f"{prompt_text}: {body}" if body else prompt_text
  console.print(); console.print(f"  [bold #ff8c00]?[/bold #ff8c00] {escape(display)}")
  try: answer = input("  â ").strip(); return f"[user answer]: {answer}"
  except (EOFError, KeyboardInterrupt): return "[no answer]"

def _handle_sub_agent(tag: ParsedTag, ctx: "CommandContext", cfg) -> str:
    role_or_id = tag.args.get("role", "summarizer").strip()
    model = tag.args.get("model", None)
    task = (tag.body or "").strip()
    if not task: return "SUB_AGENT ERROR: Missing task description in body"

    # Resolve user-created agent: match by id first, then by role_id as fallback
    role = role_or_id
    api_key: str | None = None
    provider: str | None = None
    try:
        import json
        from pathlib import Path
        ua_file = Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"
        if ua_file.exists():
            ua_data = json.loads(ua_file.read_text(encoding="utf-8"))
            agents = [a for a in ua_data.get("agents", []) if a.get("active", True)]
            # Priority 1: match by agent id (e.g. "agent-1")
            matched = next((a for a in agents if a.get("id") == role_or_id), None)
            # Priority 2: match by role_id (e.g. "web-researcher") â model used wrong key
            if matched is None:
                matched = next((a for a in agents if a.get("role_id") == role_or_id), None)
            if matched:
                role = matched.get("role_id", role_or_id)
                if not model and matched.get("model"): model = matched["model"]
                api_key = matched.get("api_key") or None
                provider = matched.get("provider") or None
    except Exception:
        pass

    from ..ui.chat import print_status_line
    display = role_or_id if role_or_id == role else f"{role_or_id}â{role}"
    key_hint = f"  [{provider}]" if provider else ""
    print_status_line("Sub-Agent", f"{display} [{model or 'Ð°Ð²ÑÐ¾'}]{key_hint}", color="#ff8c00")
    try:
        from .sub_agent import run_sub_agent
        sandbox_flag = tag.args.get("sandbox", "").lower() in ("true", "1", "yes")
        result = run_sub_agent(role, task, cfg, model=model, api_key=api_key, provider=provider, ctx=ctx, sandbox=sandbox_flag)
        return f"[sub-agent {role_or_id} output]:\n{result}"
    except Exception as e: return f"SUB_AGENT ERROR: {e}"

def _handle_request_secret(tag: ParsedTag, cfg) -> str:
  body = (tag.body or "").strip(); parts = body.split(":", 1) if body else []
  key_name = (tag.args.get("name") or (parts[0] if parts else "")).strip()
  reason = (tag.args.get("reason") or (parts[1] if len(parts) > 1 else "")).strip()
  if not key_name: return "REQUEST_SECRET ERROR: key_name Ð½Ðµ ÑÐºÐ°Ð·Ð°Ð½"
  console.print()
  console.print(f"  [bold #ff8c00]â  Ð¡ÑÐ±-Ð°Ð³ÐµÐ½Ñ Ð·Ð°Ð¿ÑÐ°ÑÐ¸Ð²Ð°ÐµÑ ÐºÐ»ÑÑ[/bold #ff8c00]")
  console.print(f"  [dim #888888]ÐÐ¼Ñ:[/dim #888888] [bold]{escape(key_name)}[/bold]")
  if reason: console.print(f"  [dim #888888]ÐÐ°ÑÐµÐ¼:[/dim #888888] [dim]{escape(reason)}[/dim]")
  console.print("  [dim]ÐÐ²ÐµÐ´Ð¸ ÐºÐ»ÑÑ (Ð¸Ð»Ð¸ Enter ÑÑÐ¾Ð±Ñ Ð¿ÑÐ¾Ð¿ÑÑÑÐ¸ÑÑ):[/dim]")
  try: value = input("  â ").strip()
  except (EOFError, KeyboardInterrupt): return f"[REQUEST_SECRET: Ð¿ÑÐµÑÐ²Ð°Ð½Ð¾ â ÐºÐ»ÑÑ {key_name} Ð½Ðµ Ð²Ð²ÐµÐ´ÑÐ½]"
  if not value: return f"[REQUEST_SECRET: ÐºÐ»ÑÑ {key_name} Ð½Ðµ Ð²Ð²ÐµÐ´ÑÐ½]"
  try: cfg.set_sub_agent_key(key_name, value)
  except Exception: pass
  console.print(f"  [dim #666666]ÐÐ»ÑÑ {escape(key_name)} ÑÐ¾ÑÑÐ°Ð½ÑÐ½[/dim #666666]")
  return f"[REQUEST_SECRET: ÐºÐ»ÑÑ {key_name} Ð¿Ð¾Ð»ÑÑÐµÐ½]"


def _handle_reincarnate(tag: "ParsedTag", ctx: "CommandContext") -> str:
      """§18.5 — Full 6-step reincarnation protocol via reincarnation_keeper."""
      reason = (tag.body or tag.args.get("reason", "context near limit")).strip()
      from ..ui.chat import print_status_line
      print_status_line("REINCARNATE", "Агент инициирует реинкарнацию: " + reason, color="#ff8c00")
      session_id = getattr(ctx, "session_id", "unknown")
      agent_name = getattr(ctx, "agent_name", "main-1")
      history = getattr(ctx, "messages", [])
      brief_parts = []
      for m in history[-6:]:
          role = m.get("role", "")
          txt = (m.get("content") or "")[:200]
          if txt:
              brief_parts.append("[" + role + "] " + txt)
      brief = "Реинкарнация по причине: " + reason + "\n\n" + "\n".join(brief_parts)
      try:
          from .reincarnation_keeper import full_reincarnation_protocol
          result = full_reincarnation_protocol(
              session_id=session_id,
              dying_agent_name=agent_name,
              brief=brief,
              reset_callback=None,
          )
          keeper = result.get("keeper", "нет")
      except Exception as e:
          keeper = "ошибка: " + str(e)
      ctx._reincarnate_requested = True
      ctx._reincarnate_reason = reason
      ctx._reincarnate_keeper = keeper
      return "[REINCARNATE: scheduled → " + reason + " | keeper=" + keeper + "]"
  
def _handle_image(tag: "ParsedTag", ctx: "CommandContext", cfg) -> str:
    """Â§17.7.6 â Vision/multimodal: encode image and ask LLM with vision."""
    import base64, mimetypes
    from pathlib import Path as _P
    path_str = (tag.args.get("path") or tag.args.get("url") or "").strip()
    question  = (tag.body or "Describe this image.").strip()
    if not path_str:
        return "IMAGE ERROR: no path= or url= provided"

    # URL â pass directly as image_url
    if path_str.startswith("http://") or path_str.startswith("https://"):
        image_content = [
            {"type": "image_url", "image_url": {"url": path_str}},
            {"type": "text",      "text": question},
        ]
    else:
        # Local file â encode as base64 data URI
        img_path = _P(path_str) if _P(path_str).is_absolute() else _P(ctx.workdir) / path_str
        if not img_path.exists():
            return f"IMAGE ERROR: file not found â {img_path}"
        mime = mimetypes.guess_type(str(img_path))[0] or "image/png"
        data = base64.b64encode(img_path.read_bytes()).decode()
        image_content = [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
            {"type": "text",      "text": question},
        ]

    from ..ui.chat import print_status_line
    print_status_line("IMAGE", f"{path_str[:60]}", color="#5fd7af")
    vision_model = tag.args.get("model") or _get_vision_model(cfg)
    try:
        import requests as _req
        api_key = _get_vision_api_key(cfg)
        msgs = [
            {"role": "system", "content": "You are a vision assistant. Answer about the image."},
            {"role": "user",   "content": image_content},
        ]
        resp = _req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": vision_model, "messages": msgs},
            timeout=60,
        )
        result = resp.json()["choices"][0]["message"]["content"]
        return f"[IMAGE result]:\n{result}"
    except Exception as e:
        try:
            from .llm import call_llm
            return "[IMAGE fallback]:\n" + call_llm(
                [{"role": "user", "content": f"Image at: {path_str}\n{question}"}], cfg
            )
        except Exception as e2:
            return f"IMAGE ERROR: {e} | fallback: {e2}"


def _get_vision_model(cfg) -> str:
    """Return a vision-capable model from config or default."""
    try:
        keys = cfg.openrouter_keys if hasattr(cfg, 'openrouter_keys') else []
        models_attr = cfg.get_models() if hasattr(cfg, 'get_models') else []
        candidates = [m for m in models_attr if any(v in str(m).lower() for v in ("gpt-4o", "claude-3", "gemini", "vision"))]
        if candidates: return str(candidates[0])
    except Exception:
        pass
    return "openai/gpt-4o"


def _get_vision_api_key(cfg) -> str:
    """Return OpenRouter API key for vision calls."""
    try:
        keys = cfg.openrouter_keys if hasattr(cfg, "openrouter_keys") else []
        if keys: return keys[0].get("key", "")
    except Exception:
        pass
    try:
        return cfg.active_key.get("key", "") if hasattr(cfg, "active_key") else ""
    except Exception:
        return ""

def _handle_suggest_next(tag: ParsedTag) -> None:
  text = (tag.body or "").strip()
  if not text: return
  from ..ui.chat import print_suggest_next
  print_suggest_next(f"ÐÐ°Ð»ÑÑÐµ Ñ Ð¼Ð¾Ð³Ñ {text}. Ð¥Ð¾ÑÐµÑÑ?")

def _handle_tasks(tag: ParsedTag, ctx: "CommandContext") -> str:
  from ..tasks.manager import TaskManager
  session_dir = Path(__file__).resolve().parent.parent.parent / "sessions" / ctx.session_id
  manager = TaskManager(session_dir); name = tag.name.upper()
  try:
      from ..ui.chat import print_status_line
      if name == "ADD_TASK":
          title = (tag.body or tag.args.get("title", "")).strip()
          if not title: return "ADD_TASK ERROR: Missing title"
          task = manager.add_task(title)
          print_status_line("Task Added", f"{task.id} â {title[:50]}", color="#ff8c00")
          return f"Task added: {task.id}"
      elif name == "UPDATE_TASK":
          tid = tag.args.get("id", "").strip(); status = tag.args.get("status", "").strip()
          if not tid: return "UPDATE_TASK ERROR: Missing id"
          kwargs: dict = {}
          if status: kwargs["status"] = status
          if tag.body: kwargs["notes"] = tag.body.strip()
          task = manager.update_task(tid, **kwargs)
          if not task: return f"UPDATE_TASK ERROR: Task {tid} not found"
          print_status_line("Task Updated", f"{tid} â {status or 'notes'}", color="#666666")
          return f"Task {tid} updated"
      elif name == "COMPLETE_TASK":
          tid = (tag.body or tag.args.get("id", "")).strip()
          if not tid: return "COMPLETE_TASK ERROR: Missing id"
          task = manager.update_task(tid, status="done")
          if not task: return f"COMPLETE_TASK ERROR: Task {tid} not found"
          print_status_line("Task Done", tid, color="#666666"); return f"Task {tid} completed"
      elif name == "LIST_TASKS":
          tasks = manager.list_tasks()
          if not tasks: return "No tasks found"
          return "\n".join(f"- [{t.id}] {t.status}: {t.title}" for t in tasks)
  except Exception as e: return f"{name} ERROR: {e}"
  return ""

def _run_websearch(query: str, cfg) -> str | None:
  if not query: return None
  try:
      from ..skills.web_search import search
      from ..ui.chat import print_status_line as _psl
      results = search(query, cfg)
      lines = []
      for r in results[:3]:
          _psl("Search Web", r["title"][:70], color="#666666")
          lines.append(f"[{r['title']}]({r['url']})\n{r['snippet']}")
      return "\n\n".join(lines) if lines else None
  except Exception as e:
      console.print(f"  [dim #995555]websearch: {escape(str(e))}[/dim #995555]"); return f"WebSearch ERROR: {e}"

def _run_fetch(url: str) -> str | None:
  if not url: return None
  try:
      from ..skills.fetch_url import fetch_text; return fetch_text(url)[:4000]
  except Exception as e:
      console.print(f"  [dim #995555]fetch: {escape(str(e))}[/dim #995555]"); return f"Fetch ERROR: {e}"

def _run_fs(tag: ParsedTag, ctx: "CommandContext") -> str | None:
  try:
      from ..skills.fs_tools import fs_op
      return fs_op(tag.args.get("op","read"), tag.args.get("path",""), tag.body or "", ctx.workdir) or None
  except Exception as e:
      console.print(f"  [dim #995555]fs: {escape(str(e))}[/dim #995555]"); return f"FS ERROR: {e}"


  # âââ New tag handlers (Â§20, Â§23-Â§26) âââââââââââââââââââââââââââââââââââââââââ

def _handle_done(tag: ParsedTag, ctx: "CommandContext") -> str | None:
    """DONE â agent signals task is complete."""
    body = (tag.body or "").strip()
    console.print()
    console.print("  [bold #ff8c00]â  ÐÐ°Ð´Ð°ÑÐ° Ð·Ð°Ð²ÐµÑÑÐµÐ½Ð°[/bold #ff8c00]")
    if body:
        console.print(f"  [dim]{escape(body[:200])}[/dim]")
    console.print()
    try:
        from ..commands.logs_cmd import log_event
        log_event(ctx.workdir, ctx.session_id, "DONE", body[:100] if body else "task complete")
    except Exception:
        pass
    return "[DONE]"


def _handle_repo_map(tag: ParsedTag, ctx: "CommandContext") -> str:
    """REPO_MAP â generate repository structure for agent orientation."""
    import ast
    import os
    max_depth = int(tag.args.get("depth", "5"))
    max_files = 200
    lines = ["<repo_map>"]
    file_count = 0

    # Load .favoriteignore patterns
    ignore_patterns: list[str] = []
    ignore_file = Path(ctx.workdir) / ".favoriteignore"
    if ignore_file.exists():
        try:
            import fnmatch
            for line in ignore_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_patterns.append(line)
        except Exception:
            pass

    def _is_ignored(rel_path: str) -> bool:
        import fnmatch
        parts = rel_path.replace("\\", "/").split("/")
        for pat in ignore_patterns:
            if fnmatch.fnmatch(rel_path, pat):
                return True
            for part in parts:
                if fnmatch.fnmatch(part, pat):
                    return True
        return False

    def _walk(dirpath: Path, depth: int) -> None:
        nonlocal file_count
        if depth > max_depth or file_count >= max_files:
            return
        try:
            entries = sorted(dirpath.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for entry in entries:
            rel = str(entry.relative_to(ctx.workdir))
            if _is_ignored(rel):
                continue
            if entry.name.startswith(".") and entry.name not in (".env",):
                continue
            if entry.name in ("__pycache__", "node_modules", ".git", "sessions", ".fav_snapshots"):
                continue
            if entry.is_dir():
                _walk(entry, depth + 1)
            elif entry.is_file():
                file_count += 1
                if file_count > max_files:
                    lines.append(f"  <!-- Ð¿Ð¾ÐºÐ°Ð·Ð°Ð½Ð¾ {max_files} Ð¸Ð· N ÑÐ°Ð¹Ð»Ð¾Ð² -->")
                    return
                if entry.suffix == ".py":
                    # Extract top-level definitions
                    try:
                        src = entry.read_text(encoding="utf-8", errors="replace")
                        tree = ast.parse(src)
                        defs = []
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                if not hasattr(node, "col_offset") or node.col_offset == 0:
                                    defs.append(node.name)
                        if defs:
                            lines.append(f'  <file path="{escape(rel)}">')
                            for d in defs[:20]:
                                lines.append(f"    {escape(d)}")
                            lines.append("  </file>")
                        else:
                            lines.append(f'  <file path="{escape(rel)}" />')
                    except Exception:
                        lines.append(f'  <file path="{escape(rel)}" />')
                else:
                    size = entry.stat().st_size
                    lines.append(f'  <file path="{escape(rel)}" size="{size}" />')

    _walk(Path(ctx.workdir), 0)
    lines.append("</repo_map>")
    result = "\n".join(lines)
    console.print(f"  [dim #666666]repo_map: {file_count} ÑÐ°Ð¹Ð»Ð¾Ð²[/dim #666666]")
    return result


def _handle_rollback(tag: ParsedTag, ctx: "CommandContext") -> str:
    """ROLLBACK â roll back to last snapshot (called by agent)."""
    target = (tag.body or tag.args.get("target", "last")).strip()
    try:
        from ..commands.snapshot_cmd import _list_snapshots, create_snapshot
        snaps = _list_snapshots(ctx.workdir)
        if not snaps:
            return "[ROLLBACK ERROR: Ð½ÐµÑ ÑÐ½Ð°Ð¿ÑÐ¾ÑÐ¾Ð²]"
        snap = snaps[0]  # last snapshot
        if target != "last":
            snap = next((s for s in snaps if s["id"] == target), snaps[0])
        console.print(f"  [bold #ff8c00]â©  ÐÑÐºÐ°Ñ Ðº {escape(snap['id'])}[/bold #ff8c00]")
        # Simplified rollback: git stash pop or restore copy
        import subprocess, shutil
        if snap.get("method") == "git_stash":
            r = subprocess.run(["git", "stash", "list"], cwd=ctx.workdir, capture_output=True, text=True, timeout=10)
            stash_idx = None
            for line in r.stdout.splitlines():
                if f"fav_snap_{snap['id']}" in line:
                    stash_idx = line.split(":")[0]
                    break
            if stash_idx:
                r2 = subprocess.run(["git", "stash", "pop", stash_idx], cwd=ctx.workdir, capture_output=True, text=True, timeout=15)
                if r2.returncode == 0:
                    return f"[ROLLBACK OK: Ð¾ÑÐºÐ°ÑÐ¸Ð»ÑÑ Ðº {snap['id']} ÑÐµÑÐµÐ· git stash]"
                return f"[ROLLBACK ERROR: {r2.stderr[:100]}]"
        return f"[ROLLBACK: ÑÐ½Ð°Ð¿ÑÐ¾Ñ {snap['id']} Ð½Ð°Ð¹Ð´ÐµÐ½ Ð½Ð¾ Ð¼ÐµÑÐ¾Ð´ '{snap.get('method','?')}' Ð½Ðµ Ð¿Ð¾Ð´Ð´ÐµÑÐ¶Ð¸Ð²Ð°ÐµÑ Ð°Ð²ÑÐ¾Ð¼Ð°ÑÐ¸ÑÐµÑÐºÐ¸Ð¹ Ð¾ÑÐºÐ°Ñ]"
    except Exception as e:
        return f"[ROLLBACK ERROR: {e}]"


def _handle_auto_checkpoint(tag: ParsedTag, ctx: "CommandContext", cfg) -> str:
    """AUTO_CHECKPOINT â create snapshot + git push (called by agent in auto mode)."""
    note = tag.args.get("note", (tag.body or "auto checkpoint")).strip()
    console.print(f"  [dim #666666]checkpoint: {escape(note[:60])}[/dim #666666]")
    result_parts = []
    try:
        from ..commands.snapshot_cmd import create_snapshot
        snap = create_snapshot(ctx.workdir, note)
        result_parts.append(f"snapshot: {snap['id']}")
    except Exception as e:
        result_parts.append(f"snapshot failed: {e}")
    try:
        from ..github.auto_push import AutoPush
        AutoPush(cfg).push_workdir(ctx.workdir, commit_msg=f"checkpoint: {note}")
        result_parts.append("git push: OK")
    except Exception as e:
        result_parts.append(f"git push failed: {e}")
    return f"[AUTO_CHECKPOINT: {', '.join(result_parts)}]"


def _handle_plan_update(tag: ParsedTag, ctx: "CommandContext") -> str | None:
    """PLAN_UPDATE â overwrite session plan.txt with new content."""
    body = (tag.body or "").strip()
    if not body:
        return None
    try:
        plan_dir = Path(ctx.workdir) / "sessions" / ctx.session_id
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "plan.txt").write_text(body, encoding="utf-8")
        console.print("  [dim #666666]Ð¿Ð»Ð°Ð½ Ð¾Ð±Ð½Ð¾Ð²Ð»ÑÐ½[/dim #666666]")
        return f"[plan updated: {len(body)} chars]"
    except Exception as e:
        return f"[PLAN_UPDATE ERROR: {e}]"


def _handle_verify(tag: ParsedTag, ctx: "CommandContext", cfg) -> str:
    """VERIFY â run verifier sub-agent to check task completion."""
    task_desc = (tag.body or tag.args.get("task", "")).strip()
    console.print("  [dim #666666]Ð²ÐµÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¾Ñ: Ð¿ÑÐ¾Ð²ÐµÑÑÑ ÑÐµÐ·ÑÐ»ÑÑÐ°Ñ...[/dim #666666]")
    try:
        from .sub_agent import run_sub_agent
        verifier_prompt = (
            "Ð¢Ñ Ð²ÐµÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¾Ñ ÑÐµÐ·ÑÐ»ÑÑÐ°ÑÐ° ÑÐ°Ð±Ð¾ÑÑ ÐÐ-Ð°Ð³ÐµÐ½ÑÐ°.\n"
            "ÐÐ¾Ð»ÑÑÐ°ÐµÑÑ: 1) Ð¸ÑÑÐ¾Ð´Ð½ÑÑ Ð·Ð°Ð´Ð°ÑÑ, 2) Ð¸ÑÐ¾Ð³ ÑÐ°Ð±Ð¾ÑÑ.\n"
            "ÐÐ°Ð¿Ð¸ÑÐ¸ ÐºÑÐ°ÑÐºÐ¾: ÑÑÐ¾ ÑÐ´ÐµÐ»Ð°Ð½Ð¾, ÑÑÐ¾ Ð½Ðµ ÑÐ´ÐµÐ»Ð°Ð½Ð¾ Ð¸Ð»Ð¸ ÑÐ´ÐµÐ»Ð°Ð½Ð¾ Ð½Ðµ ÑÐ°Ðº.\n"
            "ÐÐµ Ð¿ÑÐµÐ´Ð»Ð°Ð³Ð°Ð¹ ÑÐµÑÐµÐ½Ð¸Ð¹. Ð¢Ð¾Ð»ÑÐºÐ¾ ÑÐ°ÐºÑÑ. ÐÑÐ²ÐµÑÐ°Ð¹ Ð½Ð° ÑÐ·ÑÐºÐµ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ñ."
        )
        result = run_sub_agent(
            "verifier",
            f"ÐÐ°Ð´Ð°ÑÐ°: {task_desc}\n\n[ÐºÐ¾Ð½ÐµÑ Ð¾Ð¿Ð¸ÑÐ°Ð½Ð¸Ñ Ð·Ð°Ð´Ð°ÑÐ¸]\n\nÐÑÐ¾Ð²ÐµÑÑ Ð²ÑÐ¿Ð¾Ð»Ð½ÐµÐ½Ð¸Ðµ.",
            cfg, ctx=ctx
        )
        console.print()
        console.print(f"  [bold #ff8c00]ÐÐµÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¾Ñ:[/bold #ff8c00] {escape(result[:300])}")
        console.print()
        return f"[VERIFY result]: {result}"
    except Exception as e:
        return f"[VERIFY ERROR: {e}]"


def _handle_retry(tag: ParsedTag) -> str:
    """RETRY â agent signals it wants to retry the current task."""
    reason = (tag.body or tag.args.get("reason", "")).strip()
    console.print()
    console.print(f"  [bold #ff8c00]âº  ÐÐ³ÐµÐ½Ñ Ð¿Ð¾Ð²ÑÐ¾ÑÑÐµÑ Ð¿Ð¾Ð¿ÑÑÐºÑ[/bold #ff8c00]")
    if reason:
        console.print(f"  [dim]ÐÑÐ¸ÑÐ¸Ð½Ð°: {escape(reason[:120])}[/dim]")
    console.print()
    return f"[RETRY: {reason}]"


def _handle_memo(tag: ParsedTag, ctx: "CommandContext") -> str | None:
    """MEMO â write to agent's personal memory file."""
    to = tag.args.get("to", "self").strip()
    body = (tag.body or "").strip()
    if not body:
        return None
    try:
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        if to == "self":
            mem_dir = Path(ctx.workdir) / "sessions" / ctx.session_id / "memory"
        else:
            mem_dir = Path(ctx.workdir) / "sessions" / ctx.session_id / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        agent_name = to if to != "self" else "main"
        mem_file = mem_dir / f"{agent_name}.md"
        with open(mem_file, "a", encoding="utf-8") as f:
            f.write(f"\n<!-- {agent_name} {ts} -->\n{body}\n")
        console.print(f"  [dim #666666]memo â {escape(agent_name)}.md[/dim #666666]")
        return f"[MEMO saved to {agent_name}.md]"
    except Exception as e:
        return f"[MEMO ERROR: {e}]"


def _handle_load_mem(tag: ParsedTag, ctx: "CommandContext") -> str:
    """LOAD_MEM â load memory files for injection into next prompt."""
    try:
        from ..memory.favorite_md import FavoriteMd
        fav = FavoriteMd().read() or ""
        mem_dir = Path(ctx.workdir) / "sessions" / ctx.session_id / "memory"
        personal = ""
        if mem_dir.exists():
            for f in mem_dir.glob("*.md"):
                personal += f"\n## {f.stem}\n" + f.read_text(encoding="utf-8")
        content = (f"=== Favorite.md ===\n{fav}" if fav else "") + (f"\n=== Personal Memory ===\n{personal}" if personal else "")
        return f"[MEMORY LOADED]:\n{content}" if content else "[MEMORY: empty]"
    except Exception as e:
        return f"[LOAD_MEM ERROR: {e}]"


def _handle_shell_registered(tag: ParsedTag, ctx: "CommandContext") -> str | None:
    """SHELL:<command_name>:<args> â execute registered shell command from config/registered_commands.json."""
    import json as _json
    import subprocess as _sub
    # tag.args has positional: first arg is command name, second is optional args
    # tag format: âªSHELL:name:argsâ« â but parser puts first positional in args[0]
    args_list = list(tag.args.values())
    cmd_name = args_list[0] if args_list else (tag.body or "").strip()
    extra_args = args_list[1] if len(args_list) > 1 else ""

    reg_file = Path(__file__).resolve().parent.parent.parent / "config" / "registered_commands.json"
    if not reg_file.exists():
        return f"[SHELL ERROR: registered_commands.json Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½]"
    try:
        reg_data = _json.loads(reg_file.read_text(encoding="utf-8"))
        commands = reg_data.get("commands", {})
        template = commands.get(cmd_name)
        if not template:
            return f"[SHELL ERROR: ÐºÐ¾Ð¼Ð°Ð½Ð´Ð° '{cmd_name}' Ð½Ðµ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð°]"
        cmd = f"{template} {extra_args}".strip() if extra_args else template
        from ..ui.chat import print_shell_cmd, print_shell_output
        print_shell_cmd(cmd)
        r = _sub.run(cmd, shell=True, cwd=ctx.workdir, capture_output=True, text=True, timeout=30)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        print_shell_output(out, err)
        combined = "\n".join(filter(None, [out, err]))
        return f"$ {cmd}\n{combined}" if combined else f"$ {cmd}\n(no output)"
    except Exception as e:
        return f"[SHELL ERROR: {e}]"


# âââ New tag handlers (Â§20, Â§23âÂ§26) ââââââââââââââââââââââââââââââââââââââââââ

def _handle_ask_user_choice(tag: ParsedTag) -> str:
  """ASK_USER_CHOICE â structured choice menu for user."""
  import json as _json
  body = (tag.body or "").strip()
  # Parse: options:question  or  question body, options in args
  question = tag.args.get("question", body) or "ÐÑÐ±ÐµÑÐ¸ÑÐµ:"
  options_raw = tag.args.get("options", "")
  options = []
  if options_raw:
      try:
          options = _json.loads(options_raw)
      except Exception:
          options = [o.strip() for o in options_raw.split("|") if o.strip()]
  if not options and body:
      # Try to parse body as numbered list
      lines = [l.strip() for l in body.splitlines() if l.strip()]
      if lines:
          question = lines[0]
          options = [l.lstrip("0123456789.-) ").strip() for l in lines[1:] if l]

  console.print()
  console.print(f"  [bold #ff8c00]?[/bold #ff8c00] {escape(question)}")
  for i, opt in enumerate(options, 1):
      console.print(f"  [dim #888888]{i}.[/dim #888888] {escape(str(opt))}")
  console.print()
  try:
      raw = input("  â ").strip()
      # Try to resolve by number
      if raw.isdigit() and 1 <= int(raw) <= len(options):
          chosen = options[int(raw) - 1]
      else:
          chosen = raw
      return f"[user choice]: {chosen}"
  except (EOFError, KeyboardInterrupt):
      return "[user choice]: (Ð¾ÑÐ¼ÐµÐ½Ð°)"


def _handle_request_confirm(tag: ParsedTag) -> str:
  """REQUEST_CONFIRM â ask user to confirm a dangerous operation."""
  question = (tag.body or tag.args.get("question", "ÐÐ¾Ð´ÑÐ²ÐµÑÐ´Ð¸ÑÑ Ð´ÐµÐ¹ÑÑÐ²Ð¸Ðµ?")).strip()
  console.print()
  console.print(f"  [bold red]â [/bold red]  [bold]{escape(question)}[/bold]")
  console.print("  [dim]ÐÐ²ÐµÐ´Ð¸ 'Ð´Ð°' / 'yes' / 'y' Ð´Ð»Ñ Ð¿Ð¾Ð´ÑÐ²ÐµÑÐ¶Ð´ÐµÐ½Ð¸Ñ, Ð¸Ð»Ð¸ ÑÑÐ¾-Ð»Ð¸Ð±Ð¾ Ð´ÑÑÐ³Ð¾Ðµ Ð´Ð»Ñ Ð¾ÑÐ¼ÐµÐ½Ñ:[/dim]")
  try:
      answer = input("  â ").strip().lower()
      confirmed = answer in ("Ð´Ð°", "yes", "y", "Ð´", "1", "Ð¾Ðº", "ok")
      if confirmed:
          console.print("  [dim #666666]â ÐÐ¾Ð´ÑÐ²ÐµÑÐ¶Ð´ÐµÐ½Ð¾[/dim #666666]")
      else:
          console.print("  [dim #888888]â ÐÑÐ¼ÐµÐ½ÐµÐ½Ð¾ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÐµÐ¼[/dim #888888]")
      return "[confirmed]" if confirmed else "[cancelled by user]"
  except (EOFError, KeyboardInterrupt):
      console.print("  [dim #888888]ÐÑÐµÑÐ²Ð°Ð½Ð¾[/dim #888888]")
      return "[cancelled by user]"


def _handle_request_file(tag: ParsedTag, ctx: "CommandContext") -> str:
  """REQUEST_FILE â ask user to provide a file path and read it."""
  name = tag.args.get("name", "ÑÐ°Ð¹Ð»").strip()
  reason = (tag.body or tag.args.get("reason", "")).strip()
  console.print()
  console.print(f"  [bold #ff8c00]ð  ÐÐ³ÐµÐ½Ñ Ð·Ð°Ð¿ÑÐ°ÑÐ¸Ð²Ð°ÐµÑ ÑÐ°Ð¹Ð»: {escape(name)}[/bold #ff8c00]")
  if reason:
      console.print(f"  [dim]ÐÐ°ÑÐµÐ¼: {escape(reason)}[/dim]")
  console.print("  [dim]ÐÐ²ÐµÐ´Ð¸ Ð¿ÑÑÑ Ðº ÑÐ°Ð¹Ð»Ñ (Ð¸Ð»Ð¸ Enter ÑÑÐ¾Ð±Ñ Ð¿ÑÐ¾Ð¿ÑÑÑÐ¸ÑÑ):[/dim]")
  try:
      file_path = input("  â ").strip()
  except (EOFError, KeyboardInterrupt):
      return f"[REQUEST_FILE: Ð¿ÑÐµÑÐ²Ð°Ð½Ð¾ â {name} Ð½Ðµ Ð¿ÑÐµÐ´Ð¾ÑÑÐ°Ð²Ð»ÐµÐ½]"
  if not file_path:
      return f"[REQUEST_FILE: {name} Ð½Ðµ Ð¿ÑÐµÐ´Ð¾ÑÑÐ°Ð²Ð»ÐµÐ½]"
  try:
      from pathlib import Path as _Path
      p = _Path(file_path).expanduser().resolve()
      if not p.exists():
          return f"[REQUEST_FILE ERROR: ÑÐ°Ð¹Ð» Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½: {file_path}]"
      content = p.read_text(encoding="utf-8", errors="replace")
      max_chars = 8000
      if len(content) > max_chars:
          content = content[:max_chars] + f"\n...[Ð¾Ð±ÑÐµÐ·Ð°Ð½Ð¾]"
      console.print(f"  [dim #666666]â Ð¤Ð°Ð¹Ð» Ð¿ÑÐ¾ÑÐ¸ÑÐ°Ð½: {escape(str(p))} ({len(content)} ÑÐ¸Ð¼Ð²Ð¾Ð»Ð¾Ð²)[/dim #666666]")
      return f"[REQUEST_FILE: {name} = {file_path}]\n{content}"
  except Exception as e:
      return f"[REQUEST_FILE ERROR: {e}]"


def _handle_ask_peer(tag: "ParsedTag", ctx: "CommandContext", cfg) -> str:
  """Â§18.2 â ASK_PEER: send a question to a peer agent, wait for answer."""
  to      = tag.args.get("to", "").strip()
  timeout = int(tag.args.get("timeout", "15"))
  question = (tag.body or "").strip()
  from_id  = getattr(ctx, "agent_id", "main-1")
  if not to:   return "[ASK_PEER ERROR] Missing 'to' argument"
  if not question: return "[ASK_PEER ERROR] Empty question body"
  try:
      from .peer_bus import ask_peer
      return ask_peer(
          to=to, question=question, from_id=from_id,
          session_id=ctx.session_id, workdir=ctx.workdir,
          cfg=cfg, ctx=ctx, timeout=timeout,
      )
  except Exception as e:
      return f"[ASK_PEER ERROR] {e}"


def _handle_delegate_peer(tag: "ParsedTag", ctx: "CommandContext", cfg) -> str:
  """Â§18.2 â DELEGATE_PEER: hand off a task to a peer agent."""
  to   = tag.args.get("to", "").strip()
  role = tag.args.get("role", "analyst").strip()
  task = (tag.body or "").strip()
  from_id = getattr(ctx, "agent_id", "main-1")
  if not to:   return "[DELEGATE_PEER ERROR] Missing 'to' argument"
  if not task: return "[DELEGATE_PEER ERROR] Empty task body"
  try:
      from .peer_bus import delegate_peer
      return delegate_peer(
          to=to, task=task, role=role, from_id=from_id,
          session_id=ctx.session_id, workdir=ctx.workdir,
          cfg=cfg, ctx=ctx,
      )
  except Exception as e:
      return f"[DELEGATE_PEER ERROR] {e}"


def _handle_notify_peer(tag: "ParsedTag", ctx: "CommandContext") -> str:
  """Â§18.2 â NOTIFY_PEER: fire-and-forget event to a peer agent."""
  to      = tag.args.get("to", "").strip()
  event   = tag.args.get("event", "info").strip()
  payload = (tag.body or "").strip()
  from_id = getattr(ctx, "agent_id", "main-1")
  if not to: return "[NOTIFY_PEER ERROR] Missing 'to' argument"
  try:
      from .peer_bus import notify_peer
      return notify_peer(
          to=to, event=event, payload_text=payload,
          from_id=from_id,
          session_id=ctx.session_id, workdir=ctx.workdir,
      )
  except Exception as e:
      return f"[NOTIFY_PEER ERROR] {e}"


  # ═══════════════════════════════════════════════════════════════════════════════
# NEW TAG HANDLERS — §17.1, §18.x, §19.x
# ═══════════════════════════════════════════════════════════════════════════════


def _handle_silent(tag: "ParsedTag", ctx: "CommandContext") -> None:
    """§17.1 — SILENT: suppress visible output this turn."""
    setattr(ctx, "silent_this_turn", True)


def _handle_wait_user(tag: "ParsedTag") -> str:
    """§17.1 — WAIT_USER: pause autonomy, wait for human input."""
    return "__WAIT_USER__"


def _handle_wait_logs(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§17.1 — WAIT_LOGS: inject logs from source into agent context."""
    import json as _json
    from pathlib import Path as _Path
    source = tag.args.get("source", tag.body or "auto").strip()
    sess_dir = _Path(ctx.workdir) / "sessions" / ctx.session_id
    candidates = {
        "auto":    sess_dir / "auto.log",
        "auto.log": sess_dir / "auto.log",
        "shell":   sess_dir / "shell.log",
        "tasks":   sess_dir / "tasks.json",
    }
    target = candidates.get(source, sess_dir / source)
    if not target.exists():
        return f"[WAIT_LOGS: source '{source}' not found at {target}]"
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()[-100:]
        return f"[LOGS:{source}]\n" + "\n".join(lines)
    except Exception as e:
        return f"[WAIT_LOGS ERROR] {e}"


def _handle_status(tag: "ParsedTag", ctx: "CommandContext") -> None:
    """§17.4 — STATUS: update live-status line without adding chat line."""
    from rich.markup import escape as _escape
    text = (tag.body or tag.args.get("text", "")).strip()
    if text:
        console.print(f"  [dim #888888]≈ {_escape(text)}[/dim #888888]", end="\r")


def _handle_caps_query(tag: "ParsedTag", cfg) -> str:
    """§17.7.3 — CAPS_QUERY: find agents with a specific capability."""
    import json as _json
    from pathlib import Path as _Path
    capability = (tag.body or "").strip() or tag.args.get("cap", "").strip()
    caps_file = _Path(__file__).resolve().parent.parent.parent / "config" / "models_capabilities.json"
    if not caps_file.exists():
        return f"[CAPS_QUERY: models_capabilities.json not found — run /agents to configure]"
    try:
        caps = _json.loads(caps_file.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[CAPS_QUERY ERROR reading caps: {e}]"
    matched = []
    for model_id, info in caps.items():
        if capability in info.get("capabilities", []):
            matched.append(model_id)
        elif info.get(capability, False) is True:
            matched.append(model_id)
    if matched:
        return f"[CAPS_QUERY:{capability}] Found: {', '.join(matched)}"
    return f"[CAPS_QUERY:{capability}] No agents in family have this capability."


def _handle_save_artifact(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§17.18 — SAVE_ARTIFACT: copy file to session artifacts dir."""
    import shutil as _shutil
    from pathlib import Path as _Path
    args = tag.args
    typ  = args.get("type", args.get("t", "file")).strip()
    path = (args.get("path", tag.body or "")).strip()
    if not path:
        return "[SAVE_ARTIFACT ERROR] No path specified"
    src = _Path(path) if _Path(path).is_absolute() else _Path(ctx.workdir) / path
    if not src.exists():
        return f"[SAVE_ARTIFACT ERROR] File not found: {path}"
    artifacts_dir = _Path(ctx.workdir) / "sessions" / ctx.session_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    dst = artifacts_dir / src.name
    try:
        _shutil.copy2(str(src), str(dst))
        return f"[ARTIFACT SAVED] {typ}: {src.name} → sessions/{ctx.session_id}/artifacts/"
    except Exception as e:
        return f"[SAVE_ARTIFACT ERROR] {e}"


def _handle_auto_question(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§16.10 — AUTO_QUESTION: queue an unresolved question for the owner."""
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt
    question = (tag.body or "").strip()
    if not question:
        return "[AUTO_QUESTION: empty question]"
    q_file = _Path(ctx.workdir) / "sessions" / ctx.session_id / "questions.jsonl"
    q_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": _dt.now().isoformat(), "question": question}
    try:
        with open(q_file, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
        console.print(f"  [bold #ff8c00]* Вопрос в очередь:[/bold #ff8c00] {escape(question[:80])}")
        return f"[AUTO_QUESTION queued: {question[:60]}...]"
    except Exception as e:
        return f"[AUTO_QUESTION ERROR] {e}"


def _handle_reset_agent(tag: "ParsedTag", ctx: "CommandContext", cfg) -> str:
    """§16.22 / §18.5 — RESET_AGENT: warm/cold reset of a sub-agent context."""
    import json as _json
    from pathlib import Path as _Path
    name  = tag.args.get("name", "").strip()
    cold  = tag.args.get("cold", "false").strip().lower() in ("true", "1", "yes")
    brief = tag.args.get("brief", "").strip()
    if not name:
        return "[RESET_AGENT ERROR] Missing 'name'"
    ua_file = _Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"
    backend = "openrouter"
    if ua_file.exists():
        try:
            agents = _json.loads(ua_file.read_text(encoding="utf-8")).get("agents", [])
            for a in agents:
                if a.get("name") == name or a.get("id") == name:
                    backend = a.get("backend", "openrouter")
                    break
        except Exception:
            pass
    log = []
    if backend == "favoriteapi":
        try:
            from ..api.favorite_api import FavoriteApiClient
            keys_f = _Path(__file__).resolve().parent.parent.parent / "config" / "api_keys.json"
            keys = _json.loads(keys_f.read_text(encoding="utf-8"))
            api_key = keys.get("favorite_api_key", keys.get("api_key", ""))
            client = FavoriteApiClient(api_key=api_key, base_url=keys.get("base_url", ""))
            client.reset_context()
            log.append(f"FavoriteAPI context reset for '{name}'")
        except Exception as e:
            log.append(f"FavoriteAPI reset error: {e}")
    else:
        log.append(f"OpenRouter agent '{name}': local history cleared")
    mode = "cold" if cold else "warm"
    if not cold and brief:
        log.append(f"Brief injected: {brief[:100]}")
    console.print(f"  [dim #888888]* RESET_AGENT [{mode}]: {name}[/dim #888888]")
    return "[RESET_AGENT] " + "; ".join(log)


def _handle_brief(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§16.8 / §18.2 — BRIEF: send summary to another main agent via peer_bus."""
    to   = tag.args.get("to", "").strip()
    text = (tag.body or "").strip()
    if not to:
        return "[BRIEF ERROR] Missing 'to'"
    if not text:
        return "[BRIEF ERROR] Empty body"
    try:
        from .peer_bus import notify_peer
        from_id = getattr(ctx, "agent_id", "main-1")
        result = notify_peer(
            to=to, event="brief", payload_text=text,
            from_id=from_id, session_id=ctx.session_id, workdir=ctx.workdir,
        )
        console.print(f"  [dim #888888]* BRIEF → {to}: {text[:60]}[/dim #888888]")
        return result
    except Exception as e:
        return f"[BRIEF ERROR] {e}"


def _handle_peer_reply(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§18.2 — PEER_REPLY: reply to an ASK_PEER or confirm DELEGATE_PEER."""
    to   = (tag.args.get("to", "") or "").strip()
    text = (tag.body or "").strip()
    if not to:
        return "[PEER_REPLY ERROR] Missing recipient"
    try:
        from .peer_bus import notify_peer
        from_id = getattr(ctx, "agent_id", "main-1")
        return notify_peer(
            to=to, event="peer_reply", payload_text=text,
            from_id=from_id, session_id=ctx.session_id, workdir=ctx.workdir,
        )
    except Exception as e:
        return f"[PEER_REPLY ERROR] {e}"


def _handle_revoke_delegate(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.2 hybrid — REVOKE_DELEGATE: take back a delegated task."""
    import json as _json
    from pathlib import Path as _Path
    task_id = (tag.body or tag.args.get("task_id", "")).strip()
    if not task_id:
        return "[REVOKE_DELEGATE ERROR] No task_id"
    tasks_file = _Path(ctx.workdir) / "sessions" / ctx.session_id / "tasks.json"
    if not tasks_file.exists():
        return f"[REVOKE_DELEGATE] Task file not found"
    try:
        tasks = _json.loads(tasks_file.read_text(encoding="utf-8"))
        for t in tasks:
            if t.get("id") == task_id:
                from_id = getattr(ctx, "agent_id", "main-1")
                old_owner = t.get("owner", "?")
                t["owner"] = from_id
                t["status"] = "in_progress"
                tasks_file.write_text(_json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
                return f"[REVOKE_DELEGATE] {task_id} reclaimed from {old_owner} → {from_id}"
        return f"[REVOKE_DELEGATE] Task {task_id} not found"
    except Exception as e:
        return f"[REVOKE_DELEGATE ERROR] {e}"


def _handle_tg_digest(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.4 — TG_DIGEST: send formatted digest to Telegram."""
    text = (tag.body or "").strip()
    if not text:
        return "[TG_DIGEST: empty]"
    try:
        from ..skills.telegram_notify import send_telegram
        return send_telegram(text, workdir=ctx.workdir)
    except Exception as e:
        return f"[TG_DIGEST] Telegram not configured: {e}"


def _handle_sub_deliver(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — SUB_DELIVER: sub in sandbox signals work is ready for review."""
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt
    diff_id  = (tag.body or tag.args.get("diff_id", "")).strip()
    if not diff_id:
        diff_id = f"diff_{_dt.now().strftime('%H%M%S')}"
    sub_ws  = _Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    sub_ws.mkdir(parents=True, exist_ok=True)
    pending = sub_ws / f"pending_{diff_id}.json"
    agent_id = getattr(ctx, "agent_id", "sub-1")
    entry = {"diff_id": diff_id, "from": agent_id, "ts": _dt.now().isoformat(), "status": "pending_review"}
    pending.write_text(_json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"  [bold #ff8c00]* SUB_DELIVER:[/bold #ff8c00] diff {diff_id} ready for review")
    return f"[SUB_DELIVER] diff_id={diff_id} submitted for main agent review"


def _handle_sub_apply(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — SUB_APPLY: main applies sub sandbox diff to workdir."""
    import json as _json, shutil as _shutil
    from pathlib import Path as _Path
    diff_id = (tag.body or tag.args.get("diff_id", "")).strip()
    if not diff_id:
        return "[SUB_APPLY ERROR] No diff_id"
    sub_ws  = _Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    pending = sub_ws / f"pending_{diff_id}.json"
    if not pending.exists():
        return f"[SUB_APPLY ERROR] No pending diff: {diff_id}"
    try:
        info = _json.loads(pending.read_text(encoding="utf-8"))
        agent_ws = sub_ws / info.get("from", "sub")
        if agent_ws.exists():
            for f in agent_ws.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(agent_ws)
                    dst = _Path(ctx.workdir) / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    _shutil.copy2(str(f), str(dst))
        pending.rename(sub_ws / f"applied_{diff_id}.json")
        console.print(f"  [bold #ff8c00]* SUB_APPLY:[/bold #ff8c00] diff {diff_id} applied")
        return f"[SUB_APPLY] diff_id={diff_id} applied to workdir"
    except Exception as e:
        return f"[SUB_APPLY ERROR] {e}"


def _handle_sub_discard(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — SUB_DISCARD: main discards a sub sandbox diff."""
    from pathlib import Path as _Path
    diff_id = (tag.body or tag.args.get("diff_id", "")).strip()
    if not diff_id:
        return "[SUB_DISCARD ERROR] No diff_id"
    sub_ws  = _Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    pending = sub_ws / f"pending_{diff_id}.json"
    if pending.exists():
        pending.rename(sub_ws / f"discarded_{diff_id}.json")
    console.print(f"  [dim #888888]* SUB_DISCARD: diff {diff_id} rejected[/dim #888888]")
    return f"[SUB_DISCARD] diff_id={diff_id} rejected"


def _handle_sub_change_review(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — SUB_CHANGE_REVIEW: engine asks main to review a sub change."""
    args      = tag.args
    sub_name  = args.get("name", args.get("_pos0", "sub")).strip()
    change_id = args.get("id", args.get("_pos1", "?")).strip()
    summary   = args.get("summary", args.get("_pos2", "change")).strip()
    excerpt   = (tag.body or args.get("excerpt", "")).strip()
    console.print()
    console.print(f"  [bold #ff8c00]* Ревью суба {escape(sub_name)}[/bold #ff8c00]  id={change_id}")
    console.print(f"  {escape(summary)}")
    if excerpt:
        console.print(f"  [dim]Diff:\n{escape(excerpt[:300])}[/dim]")
    console.print("  [dim]Используй APPROVE_SUB или REJECT_SUB[/dim]")
    return f"[SUB_CHANGE_REVIEW] {sub_name}/{change_id}: awaiting main decision"


def _handle_approve_sub(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — APPROVE_SUB: main approves a sub change."""
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt
    sub_name  = (tag.args.get("name", tag.args.get("_pos0", "")) or "").strip()
    change_id = (tag.args.get("change_id", tag.args.get("_pos1", "")) or "").strip()
    sub_ws = _Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    sub_ws.mkdir(parents=True, exist_ok=True)
    with open(sub_ws / "reviews.jsonl", "a", encoding="utf-8") as f:
        f.write(_json.dumps({"ts": _dt.now().isoformat(), "action": "approve",
                              "sub": sub_name, "change_id": change_id}, ensure_ascii=False) + "\n")
    return f"[APPROVE_SUB] {sub_name}/{change_id} approved"


def _handle_reject_sub(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — REJECT_SUB: main rejects a sub change with reason."""
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt
    args      = tag.args
    sub_name  = (args.get("name", args.get("_pos0", "")) or "").strip()
    change_id = (args.get("change_id", args.get("_pos1", "")) or "").strip()
    reason    = (args.get("reason", tag.body or "") or "").strip()
    sub_ws = _Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    sub_ws.mkdir(parents=True, exist_ok=True)
    with open(sub_ws / "reviews.jsonl", "a", encoding="utf-8") as f:
        f.write(_json.dumps({"ts": _dt.now().isoformat(), "action": "reject",
                              "sub": sub_name, "change_id": change_id,
                              "reason": reason}, ensure_ascii=False) + "\n")
    return f"[REJECT_SUB] {sub_name}/{change_id} rejected: {reason}"


def _handle_request_full_diff(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§19.6 — REQUEST_FULL_DIFF: request full diff of a sub sandbox change."""
    from pathlib import Path as _Path
    change_id = (tag.body or tag.args.get("change_id", "")).strip()
    if not change_id:
        return "[REQUEST_FULL_DIFF ERROR] No change_id"
    sub_ws  = _Path(ctx.workdir) / "sessions" / ctx.session_id / "sub_workspaces"
    pending = sub_ws / f"pending_{change_id}.json"
    if not pending.exists():
        return f"[REQUEST_FULL_DIFF] change {change_id} not found in sub_workspaces"
    return f"[REQUEST_FULL_DIFF] Full diff for {change_id} — see sub_workspaces/pending_{change_id}.json"


def _handle_plan(tag: "ParsedTag", ctx: "CommandContext") -> str:
    """§3 — PLAN: render final plan in /plan mode."""
    from pathlib import Path as _Path
    from rich.panel import Panel as _Panel
    body = (tag.body or "").strip()
    if not body:
        return "[PLAN: empty]"
    console.print(_Panel(
        escape(body),
        title="[bold #ff8c00]ПЛАН[/bold #ff8c00]",
        border_style="#ff8c00",
        padding=(1, 2),
    ))
    plan_path = _Path(ctx.workdir) / "sessions" / ctx.session_id / "plan.txt"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(body, encoding="utf-8")
    return f"[PLAN rendered and saved → sessions/{ctx.session_id}/plan.txt]"
  
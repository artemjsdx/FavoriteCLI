"""
favorite/agent/sub_agent.py
Sub-agent runner with tool loop. Sub-agents can use websearch, shell, file ops.
"""
import json
from datetime import datetime
from pathlib import Path
from .response_processor import strip_thinking_blocks
from .tags import strip_tags, extract_tags

SUB_AGENT_DEFAULT_MODEL = "qwen/qwen3-coder:free"

_TOOLS_HEADER = """\

  ### TOOLS YOU CAN USE
  Use these tags to take real actions. Never hallucinate data.

    <CMD>any shell command</CMD>                        — ГЛАВНЫЙ инструмент: выполняет shell-команду, возвращает stdout+stderr
                                                          Таймаут 60с, лимит 5000 символов, используй абсолютные пути
                                                          Примеры:
                                                            <CMD>curl -s "https://duckduckgo.com/html/?q=python+error"</CMD>
                                                            <CMD>python3 -c "import requests; r=requests.get('https://example.com'); print(r.text[:500])"</CMD>
                                                            <CMD>ls /absolute/path/to/dir</CMD>
                                                            <CMD>cat /absolute/path/to/file.py | head -80</CMD>
    <WRITE_FILE:path=relative/path>content</WRITE_FILE> — записать файл
    <NEXT>continue message</NEXT>                       — нужна ещё одна итерация
    <CONTINUE>hint</CONTINUE>                           — ещё один ход

  ANTI-HALLUCINATION RULES:
  - Текущие данные (курсы, новости, цены) → всегда <CMD>curl ...</CMD>. Никогда не угадывай.
  - После получения ссылок → <CMD>curl -sL "URL" | head -200</CMD> для полного контента.
  - Никогда не придумывай факты, цифры, даты.
  - Current date and time: {now}
  """

_SUB_ALLOWED_TAGS = {"CMD", "SKILL", "SHELL_RAW", "READ_FILE", "WRITE_FILE", "NEXT", "CONTINUE", "THINK"}


def _is_sandbox_on(cfg=None) -> bool:
    """Check global sandbox toggle (config/modules.json → sub_agent_sandbox)."""
    try:
      from .sandbox import is_sandbox_enabled_globally
      return is_sandbox_enabled_globally(cfg)
    except Exception:
      return False


def run_sub_agent(role_id: str, task: str, cfg, model: str | None = None,
                  api_key: str | None = None, provider: str | None = None,
                  ctx=None, sandbox: bool = False) -> str:
  """
  Spawns a sub-agent with a specific role, runs a task with tool loop, returns result.
  Sub-agents can use websearch, shell, and file ops via tags.
  sandbox=True  — isolated workdir per §19.5 (opt-in), cleaned up after return.
  """
  roles_file = Path(__file__).resolve().parent / "sub_roles_library.json"
  if not roles_file.exists():
    return f"ERROR: sub_roles_library.json not found at {roles_file}"
  try:
    roles = json.loads(roles_file.read_text(encoding="utf-8"))
  except Exception as e:
    return f"ERROR: Failed to load roles library: {e}"
  role_dict = next((r for r in roles if r["id"] == role_id), None)
  if not role_dict:
    available = ", ".join(r["id"] for r in roles[:10])
    return f"ERROR: Role '{role_id}' not found. Available: {available}..."
  sub_model = (
    model
    or role_dict.get("preferred_model")
    or _cfg_sub_model(cfg)
    or SUB_AGENT_DEFAULT_MODEL
  )

  now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
  tools_block = _TOOLS_HEADER.format(now=now)
  system_content = role_dict["system_prompt"] + tools_block

  messages = [
    {"role": "system", "content": system_content},
    {"role": "user",   "content": task},
  ]
  # §19.5 — optional sandbox workdir
  _sandbox_path = None
  _sandbox_ctx = ctx
  if sandbox or _is_sandbox_on(cfg):
    try:
      from .sandbox import make_sandbox
      _sid = getattr(ctx, "session_id", "default") if ctx else "default"
      _wd  = getattr(ctx, "workdir", ".") if ctx else "."
      _sandbox_path = make_sandbox(_wd, _sid, role_id)
      if ctx is not None:
        import copy
        _sandbox_ctx = copy.copy(ctx)
        _sandbox_ctx.workdir = str(_sandbox_path)
    except Exception:
      pass  # sandbox fail → shared workdir

  try:
    result = _sub_agent_loop(messages, cfg, sub_model, api_key=api_key, provider=provider, ctx=_sandbox_ctx)
    return result
  except Exception as e:
    err = str(e)
    hint = ""
    if any(k in err.lower() for k in ("connection", "timeout", "refused", "url", "host", "resolve", "network", "ssl", "http")):
      hint = "\n⚠ Это сетевая/URL-ошибка — синтаксис тегов верен, проблема в подключении к API."
    return (
      f"[SUB-AGENT ОШИБКА] role={role_id} provider={provider or 'openrouter'} model={sub_model}\n"
      f"Причина: {err}{hint}\n"
      f"Не меняй синтаксис тегов — проблема не в нём. Сообщи пользователю об ошибке подключения."
    )
  finally:
    if _sandbox_path is not None:
      try:
        from .sandbox import cleanup_sandbox
        cleanup_sandbox(_sandbox_path)
      except Exception:
        pass

def _sub_agent_loop(messages: list[dict], cfg, sub_model: str,
                    api_key=None, provider=None, ctx=None, max_steps: int = 6) -> str:
  """Mini agent loop: call LLM → execute tool tags → feed results back → repeat."""
  for step in range(max_steps):
    raw = _call_any(messages, cfg, sub_model, api_key=api_key, provider=provider)
    tags = extract_tags(raw)
    action_tags = [t for t in tags if t.name.upper() in _SUB_ALLOWED_TAGS and t.name.upper() != "THINK"]

    if not action_tags:
      return strip_tags(strip_thinking_blocks(raw)).strip()

    tool_output = _execute_sub_tags(action_tags, cfg, ctx)
    if not tool_output:
      return strip_tags(strip_thinking_blocks(raw)).strip()

    messages.append({"role": "assistant", "content": raw})
    messages.append({"role": "user", "content": f"[tool output]\n{tool_output}"})

  raw = _call_any(messages, cfg, sub_model, api_key=api_key, provider=provider)
  return strip_tags(strip_thinking_blocks(raw)).strip()


def _execute_sub_tags(tags, cfg, ctx=None) -> str:
  """Execute tags that sub-agents are allowed to use. Lazy imports to avoid circular deps."""
  from .executor import _handle_skill, _handle_shell, _handle_read_file, _handle_write_file, _handle_next, _handle_continue
  parts: list[str] = []
  for tag in tags:
    name = tag.name.upper()
    result = None
    if name == "SKILL":
      result = _handle_skill(tag, ctx, cfg)
    elif name == "SHELL_RAW":
      if ctx is not None:
        result = _handle_shell(tag, ctx, background=False)
      else:
        result = "[SHELL_RAW unavailable in this sub-agent context]"
    elif name == "READ_FILE":
      if ctx is not None:
        result = _handle_read_file(tag, ctx)
      else:
        result = "[READ_FILE unavailable in this sub-agent context]"
    elif name == "WRITE_FILE":
      if ctx is not None:
        result = _handle_write_file(tag, ctx)
      else:
        result = "[WRITE_FILE unavailable in this sub-agent context]"
    elif name == "NEXT":
      result = _handle_next(tag)
    elif name == "CONTINUE":
      result = _handle_continue(tag)
    if result:
      parts.append(result)
  return "\n".join(parts)


def _cfg_sub_model(cfg) -> str | None:
  try:
    fav = cfg.default_favorite_key()
    if fav and fav.get("model"):
      return fav["model"]
  except Exception:
    pass
  return None


def _call_any(messages: list[dict], cfg, model: str,
              api_key: str | None = None, provider: str | None = None) -> str:
  """Use agent-specific key/provider if given; else global keys with fallback."""
  if api_key and provider:
    if provider == "openrouter":
      return _call_openrouter_direct(messages, api_key, model)
    elif provider == "favoriteapi":
      return _call_favoriteapi_direct(messages, api_key, cfg.favorite_api_base_url, model, cfg=cfg)
  or_key  = cfg.default_openrouter_key()
  fav_key = cfg.default_favorite_key()
  if not or_key and not fav_key:
    raise RuntimeError("Нет API-ключа. Добавь через /OpenRouter API или /Favorite API.")
  if or_key:
    try:
      return _call_openrouter(messages, cfg, model)
    except Exception:
      if not fav_key:
        raise
  return _call_favorite_api(messages, cfg)


def _call_openrouter_direct(messages: list[dict], key_val: str, model: str) -> str:
  import requests as req
  headers = {
    "Authorization": f"Bearer {key_val}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/animebyst07-stack/FavoriteCLI",
    "X-Title": "FavoriteCLI",
  }
  r = req.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers=headers, json={"model": model, "messages": messages}, timeout=120,
  )
  data = r.json()
  if "error" in data:
    raise RuntimeError(data["error"].get("message", str(data["error"])))
  content = data["choices"][0]["message"]["content"]
  if content is None:
    raise RuntimeError(f"Модель {model} вернула null-контент")
  return content


def _call_favoriteapi_direct(messages: list[dict], key_val: str, base_url: str, model: str | None,
                             cfg=None) -> str:
  """Call FavoriteAPI with a specific key. Uses TG bridge to resolve URL on failure."""
  from ..bridge import tg_url as _tg_url
  from .llm import _inject_system_into_messages
  import requests as req

  def _do_post(url: str) -> str:
    h = {"Authorization": f"Bearer {key_val}", "Content-Type": "application/json"}
    processed = _inject_system_into_messages(messages)
    body: dict = {"messages": processed}
    if model: body["model"] = model
    r = req.post(f"{url}/api/v1/chat", headers=h, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    cnt = data["choices"][0]["message"]["content"]
    if cnt is None: raise RuntimeError("FavoriteAPI вернула null-контент")
    return cnt

  try:
    return _do_post(base_url)
  except Exception:
    if cfg is None or not cfg.has_tg_bridge():
      raise
    fresh_url = _tg_url.fetch_url(cfg.tg_bridge_token, cfg.tg_bridge_chat_id)
    if not fresh_url or fresh_url == base_url:
      raise
    cfg.set_favorite_api_base_url(fresh_url)
    return _do_post(fresh_url)


def _call_openrouter(messages, cfg, model):
  from .llm import call_llm
  return call_llm(messages, cfg)


def _call_favorite_api(messages, cfg):
  from .llm import call_llm
  return call_llm(messages, cfg)

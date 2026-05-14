"""
favorite/agent/llm.py
LLM call helpers: blocking call + SSE streaming (OpenRouter only).
"""
from __future__ import annotations

import json
from typing import Iterator

# §39.3 — Key rotation + §30.2 Token usage (lazy imports to avoid circular)
def _record_usage(model: str, pt: int, ct: int, backend: str) -> None:
    try:
        from favorite.token_usage import record as _tu_record
        _tu_record(model=model, prompt_tokens=pt, completion_tokens=ct, backend=backend)
    except Exception:
        pass

def _handle_api_error(provider: str, status_code: int) -> str | None:
    """Try to rotate API key on 429/401. Returns new key or None."""
    try:
        from favorite.key_rotation import handle_error
        return handle_error(provider, status_code)
    except Exception:
        return None


def _inject_system_into_messages(messages: list[dict]) -> list[dict]:
  """
  FavoriteAPI and some Gemini-based APIs do NOT support role='system'.
  Extracts system messages and prepends their content to the first user message.
  """
  system_parts: list[str] = []
  other: list[dict] = []
  for msg in messages:
      if msg.get("role") == "system":
          system_parts.append(msg["content"])
      else:
          other.append(dict(msg))

  if not system_parts or not other:
      return messages

  system_text = "\n\n".join(system_parts)

  for i, msg in enumerate(other):
      if msg.get("role") == "user":
          other[i] = {
              "role": "user",
              "content": f"[SYSTEM INSTRUCTIONS]\n{system_text}\n\n[USER MESSAGE]\n{msg['content']}",
          }
          break
  else:
      other.insert(0, {"role": "user", "content": f"[SYSTEM INSTRUCTIONS]\n{system_text}"})

  # BUG FIX 5: If history is long, inject a reminder into the LAST message
  if len(other) >= 10:
      last_msg = other[-1]
      if last_msg.get("role") == "user":
          # Find workdir from system_text if possible, or just use a generic reminder
          import re
          workdir_match = re.search(r"Working directory: (.*)", system_text)
          workdir = workdir_match.group(1) if workdir_match else "unknown"
          
          reminder = f"\n\n[SYSTEM REMINDER: You are Favorite CLI agent. Working dir: {workdir}]"
          if reminder not in last_msg["content"]:
              last_msg["content"] += reminder

  return other


def _build_favoriteapi_body(messages: list[dict], cfg, model_override: str | None = None) -> dict:
  """
  Build request body for FavoriteAPI.
  - Injects system prompt into user message (Gemini doesn't support role=system)
  - model_override: model from RouterModule.select_model() (e.g. from user_agents.json)
  - Falls back to cfg.default_favorite_key() model if no override
  """
  processed = _inject_system_into_messages(messages)
  body: dict = {"messages": processed}
  model = model_override
  if not model:
      fav = cfg.default_favorite_key()
      if fav and fav.get("model"):
          model = fav["model"]
  if model:
      body["model"] = model
  return body


def call_llm(messages: list[dict], cfg) -> str:
  """Blocking LLM call. Returns full response text."""
  import requests as req
  from .response_processor import strip_thinking_blocks
  from .model_router import RouterModule

  prompt = messages[-1]["content"] if messages else ""

  try:
      provider_name, model_name, api_key = RouterModule.select_model(prompt, cfg)

      if provider_name == "NVIDIA":
          headers = {
              "Authorization": f"Bearer {api_key}",
              "Content-Type": "application/json",
          }
          body = {"model": model_name, "messages": messages}
          r = req.post(
              "https://integrate.api.nvidia.com/v1/chat/completions",
              headers=headers, json=body, timeout=120,
          )
          r.raise_for_status()
          response_text = strip_thinking_blocks(r.json()["choices"][0]["message"]["content"])
          # §30.2 — Record token usage
          _record_usage(
              model=str(model_name),
              pt=sum(len(str(m.get("content","")).split()) for m in messages),
              ct=len(response_text.split()),
              backend=str(provider_name),
          )
          return response_text

      if provider_name == "OpenRouter":
          headers = {
              "Authorization": f"Bearer {api_key}",
              "Content-Type": "application/json",
              "HTTP-Referer": "https://github.com/animebyst07-stack/FavoriteCLI",
              "X-Title": "FavoriteCLI",
          }
          body = {"model": model_name, "messages": messages}
          r = req.post(
              "https://openrouter.ai/api/v1/chat/completions",
              headers=headers, json=body, timeout=120,
          )
          data = r.json()
          if "error" in data:
              raise RuntimeError(data["error"].get("message", str(data["error"])))
          return strip_thinking_blocks(data["choices"][0]["message"]["content"])

      if provider_name == "FavoriteAPI":
          headers = {
              "Authorization": f"Bearer {api_key}",
              "Content-Type": "application/json",
          }
          body = _build_favoriteapi_body(messages, cfg, model_override=model_name)
          r = req.post(
              f"{cfg.favorite_api_base_url}/api/v1/chat",
              headers=headers, json=body, timeout=90,
          )
          r.raise_for_status()
          return strip_thinking_blocks(r.json()["choices"][0]["message"]["content"])

  except Exception as _llm_err:
      import sys, time as _time
      print(f"[LLM primary error: {_llm_err}]", file=sys.stderr, flush=True)
      # FIX-6: при 429 rate limit — сразу fallback, без медленных retries
      _is_429 = any(x in str(_llm_err).lower() for x in ("429", "rate limit", "quota", "too many"))
      if not _is_429:
          _time.sleep(2)
          try:
              _rr = req.post(
                  "https://openrouter.ai/api/v1/chat/completions",
                  headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                           "HTTP-Referer": "https://github.com/animebyst07-stack/FavoriteCLI", "X-Title": "FavoriteCLI"},
                  json={"model": model_name, "messages": messages}, timeout=120,
              )
              _rd = _rr.json()
              if "error" not in _rd:
                  return strip_thinking_blocks(_rd["choices"][0]["message"]["content"])
          except Exception as _re:
              print(f"[LLM single-retry failed: {_re}]", file=sys.stderr, flush=True)
      else:
          print(f"[LLM 429 detected — instant fallback to FavoriteAPI]", file=sys.stderr, flush=True)

  # --- FALLBACK CHAIN: OR → FavoriteAPI → error ---
  # BUG FIX: or_key["model"] is explicitly None when key is a raw string,
  # so use `or` instead of dict.get() default to handle None properly.
  # BUG FIX 2: wrap OR fallback in try/except so FavoriteAPI is tried on rate-limit.
  or_key = cfg.default_openrouter_key()
  if or_key:
      try:
          headers = {
              "Authorization": f"Bearer {or_key['key']}",
              "Content-Type": "application/json",
              "HTTP-Referer": "https://github.com/animebyst07-stack/FavoriteCLI",
              "X-Title": "FavoriteCLI",
          }
          body = {
              "model": or_key.get("model") or "qwen/qwen3-coder:free",
              "messages": messages,
          }
          r = req.post(
              "https://openrouter.ai/api/v1/chat/completions",
              headers=headers, json=body, timeout=120,
          )
          data = r.json()
          if "error" in data:
              import sys as _sys
              _sys.stderr.write(f"[LLM OR fallback error: {data['error'].get('message','?')}] → trying FavoriteAPI\n")
          else:
              return strip_thinking_blocks(data["choices"][0]["message"]["content"])
      except Exception as _or_fb_err:
          import sys as _sys
          _sys.stderr.write(f"[LLM OR fallback exception: {_or_fb_err}] → trying FavoriteAPI\n")

  fav = cfg.default_favorite_key()
  if fav:
      headers = {
          "Authorization": f"Bearer {fav['key']}",
          "Content-Type": "application/json",
      }
      body = _build_favoriteapi_body(messages, cfg)
      r = req.post(
          f"{cfg.favorite_api_base_url}/api/v1/chat",
          headers=headers, json=body, timeout=90,
      )
      r.raise_for_status()
      return strip_thinking_blocks(r.json()["choices"][0]["message"]["content"])

  raise RuntimeError("Нет доступного провайдера.")


def stream_llm(messages: list[dict], cfg) -> Iterator[str]:
  """
  SSE streaming for OpenRouter only.
  Yields text chunks as they arrive, suppressing <thinking> blocks.
  Raises RuntimeError if OpenRouter key not configured — caller should fallback.
  """
  import requests as req

  or_key = cfg.default_openrouter_key()
  if not or_key:
      raise RuntimeError("stream_llm: OpenRouter ключ не найден")

  # FIX: RouterModule selects model from user_agents.json
  try:
      from .model_router import RouterModule as _RM
      _msg = messages[-1]['content'] if messages else ''
      _prov, _model, _rkey = _RM.select_model(_msg, cfg)
      use_key = _rkey or or_key['key']
      use_model = _model if _prov == 'OpenRouter' else (or_key.get('model') or 'qwen/qwen3-coder:free')
  except Exception:
      use_key = or_key['key']
      use_model = or_key.get('model') or 'qwen/qwen3-coder:free'

  headers = {
      "Authorization": f"Bearer {use_key}",
      "Content-Type": "application/json",
      "HTTP-Referer": "https://github.com/animebyst07-stack/FavoriteCLI",
      "X-Title": "FavoriteCLI",
  }
  body = {
      "model": use_model,
      "messages": messages,
      "stream": True,
  }

  in_thinking = False
  buffer = ""

  with req.post(
      "https://openrouter.ai/api/v1/chat/completions",
      headers=headers, json=body, stream=True, timeout=90,
  ) as r:
      r.raise_for_status()
      for raw_line in r.iter_lines():
          if not raw_line:
              continue
          if raw_line == b"data: [DONE]":
              break
          if raw_line.startswith(b"data: "):
              try:
                  data = json.loads(raw_line[6:])
              except json.JSONDecodeError:
                  continue
              delta = (
                  data.get("choices", [{}])[0]
                  .get("delta", {})
                  .get("content", "")
              )
              if not delta:
                  continue

              buffer += delta

              while buffer:
                  if not in_thinking:
                      if "<thinking" in buffer:
                          start_idx = buffer.find("<thinking")
                          if ">" in buffer[start_idx:]:
                              end_tag_idx = buffer.find(">", start_idx) + 1
                              if start_idx > 0:
                                  yield buffer[:start_idx]
                              in_thinking = True
                              buffer = buffer[end_tag_idx:]
                          else:
                              if start_idx > 0:
                                  yield buffer[:start_idx]
                                  buffer = buffer[start_idx:]
                              break
                      else:
                          yield buffer
                          buffer = ""
                  else:
                      if "</thinking>" in buffer:
                          end_idx = buffer.find("</thinking>") + len("</thinking>")
                          in_thinking = False
                          buffer = buffer[end_idx:]
                      elif "</thinking" in buffer:
                          break
                      else:
                          buffer = ""
                          break

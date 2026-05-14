# FIX-6: заменяем медленный backoff на быстрый 429-check
import re
fpath = "/storage/emulated/0/Цхранилище/Project/FavoriteCLI/favorite/agent/llm.py"
content = open(fpath, encoding="utf-8").read()

# Находим и заменяем блок retry с backoff
pattern = r"(      # Fix [А-Я\w]+: retry with exponential backoff[^\n]*\n)      for _delay in \(1, 2, 4\):[\s\S]*?print\(f\"\[LLM retry \{_delay\}s failed.*?\n"

new_block = """      # FIX-6: при 429 rate limit — сразу fallback, без медленных retries
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
"""

if "for _delay in (1, 2, 4):" in content:
    new_content = re.sub(pattern, new_block, content, flags=re.MULTILINE)
    if new_content != content:
        open(fpath, "w", encoding="utf-8").write(new_content)
        print("FIX-6 APPLIED OK")
    else:
        # Fallback: simple string replace
        idx = content.find("for _delay in (1, 2, 4):")
        # Find the block end
        end_marker = "print(f\"[LLM retry {_delay}s failed"
        end_idx = content.find(end_marker)
        if end_idx > 0:
            end_line_end = content.find("\n", end_idx) + 1
            start_comment = content.rfind("      # Fix", 0, idx)
            old_block = content[start_comment:end_line_end]
            new_content2 = content.replace(old_block, new_block)
            open(fpath, "w", encoding="utf-8").write(new_content2)
            print("FIX-6 APPLIED via string replace")
        else:
            print("FIX-6 FAILED: end marker not found")
else:
    print("FIX-6: for _delay block not found — already patched?")
    if "_is_429" in content:
        print("FIX-6 already applied")

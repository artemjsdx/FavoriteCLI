"""
favorite/skills/web_search.py
WebSearch скилл: VoidAI perplexity/sonar → DuckDuckGo HTML fallback.

VoidAI API: https://api.voidai.app/v1/chat/completions (OpenAI-compatible)
  — использует ключ cfg.void_ai_key (формат sk-va-unified-...)
  — модель: perplexity/sonar

OpenRouter fallback: https://openrouter.ai/api/v1/chat/completions
  — использует OR-ключ, модель perplexity/sonar (если доступна)
"""
import json
import re
import urllib.request
import urllib.parse
from typing import Optional

_VOIDAI_URL  = "https://api.voidai.app/v1/chat/completions"
_OR_URL      = "https://openrouter.ai/api/v1/chat/completions"
_SONAR_MODEL = "perplexity/sonar"


def search(query: str, cfg) -> list[dict]:
    """Возвращает список {"title", "snippet", "url"}. До 5 результатов."""
    provider = "auto"
    try:
        provider = cfg.skill_setting("WebSearch", "provider", "auto")
    except Exception:
        pass

    if provider == "ddg":
        return _ddg_fallback(query)
    if provider == "voidai":
        return _void_ai_search(query, cfg)
    # auto: try VoidAI first, fall back to DDG
    results = _void_ai_search(query, cfg)
    if results:
        return results
    return _ddg_fallback(query)


def _build_messages(query: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a real-time web search assistant. "
                "Always provide EXACT current numbers, prices, rates, dates from live sources. "
                "Do NOT say approximate values. Do NOT make up numbers. "
                "Always cite the source URL for each fact."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{query}\n\n"
                "Provide EXACT current values with numbers. "
                "Format each fact as: [VALUE] — source: [URL]"
            ),
        },
    ]


def _call_api(url: str, api_key: str, query: str, referer: str = "") -> list[dict]:
    """Общая функция вызова OpenAI-совместимого API для поиска."""
    payload = json.dumps({
        "model": _SONAR_MODEL,
        "messages": _build_messages(query),
    }).encode("utf-8")

    req_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if referer:
        req_headers["HTTP-Referer"] = referer
        req_headers["X-Title"] = "FavoriteCLI"

    req = urllib.request.Request(url, data=payload, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    content = data["choices"][0]["message"]["content"]
    if not content or len(content) < 20:
        return []
    return [{"title": f"VoidAI/Sonar (live search)", "snippet": content[:3000], "url": ""}]


def _void_ai_search(query: str, cfg) -> list[dict]:
    """
    Поиск через VoidAI API (perplexity/sonar).
    
    Приоритет ключей:
    1. cfg.void_ai_key (нативный VoidAI ключ sk-va-unified-...) → _VOIDAI_URL
    2. OpenRouter ключ → _OR_URL (как fallback, если VoidAI ключ не задан)
    """
    try:
        # 1. Попробовать VoidAI native key
        void_key = getattr(cfg, "void_ai_key", None) or ""
        if void_key and void_key.startswith("sk-va-"):
            return _call_api(_VOIDAI_URL, void_key, query)

        # 2. Fallback: OpenRouter key через OpenRouter endpoint
        or_key_data = cfg.default_openrouter_key()
        if or_key_data:
            or_key = or_key_data.get("key", "")
            if or_key:
                return _call_api(
                    _OR_URL, or_key, query,
                    referer="https://github.com/animebyst07-stack/FavoriteCLI"
                )

        return []
    except Exception:
        return []


def _ddg_fallback(query: str) -> list[dict]:
    """DuckDuckGo HTML scrape — без JS, без API-ключа."""
    try:
        q = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={q}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results = []
        blocks = re.findall(
            r'<div[^>]+class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html, re.DOTALL,
        )
        for block in blocks:
            url_match = re.search(r'href="(https?://[^"]+)"', block)
            raw_url = url_match.group(1) if url_match else ""
            if "duckduckgo.com" in raw_url:
                continue
            title_match = re.search(r'<(?:a|h2)[^>]*>(.*?)</(?:a|h2)>', block, re.DOTALL)
            title = _clean(title_match.group(1)) if title_match else ""
            snip_match = re.search(
                r'class="[^"]*snippet[^"]*"[^>]*>(.*?)</(?:div|span|a)>', block, re.DOTALL
            )
            snippet = _clean(snip_match.group(1)) if snip_match else _clean(block)[:500]
            if not title and not snippet:
                continue
            results.append({"title": title[:200], "snippet": snippet[:600], "url": raw_url})
            if len(results) >= 5:
                break

        return results
    except Exception:
        return []


def _clean(html: str) -> str:
    """Убирает HTML-теги и нормализует пробелы."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#x27;|&quot;", "'", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

class WebSearchSkill:
    @property
    def name(self): return 'WebSearch'
    def run(self,q,cfg=None,ctx=None):
        r=search(q,cfg) or []
        return '\n'.join('- '+x.get('title','') for x in r) or 'No results.'
    def search(self,q,cfg=None): return search(q,cfg)
    def execute(self,q,cfg=None,ctx=None): return self.run(q,cfg,ctx)

WebsearchSkill=WebSearchSkill

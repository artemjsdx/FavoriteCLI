"""
favorite/skills/internet_skill.py
Internet (browser automation) skill — requires FavoriteChrome local server.
See: https://github.com/artemjsdx/FavoriteChrome
"""
import json
from pathlib import Path
from .base import ISkill

_CHROME_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "favorite_chrome.json"


def _load_token() -> str | None:
    if _CHROME_CONFIG.exists():
        try:
            data = json.loads(_CHROME_CONFIG.read_text(encoding="utf-8"))
            return data.get("device_token")
        except Exception:
            pass
    return None


class InternetSkill(ISkill):
    name = "internet"
    description = "Browser automation via FavoriteChrome (screenshot, interact). Requires local server."
    _prompt_snippet = (
        "Skill: internet — управление браузером через FavoriteChrome (скриншоты, клики, OCR).\n"
        "Usage: <SKILL:name=internet.screenshot>url: https://example.com\nfull_page: false</SKILL>"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "").strip()
        token = _load_token()
        if not token:
            return (
                "[internet: скилл не настроен. Привяжи FavoriteChrome:\n"
                "  1. Запусти FavoriteChrome: python server.py\n"
                "  2. Зайди на http://localhost:5006/account/link\n"
                "  3. Выполни /skills internet on]"
            )
        # Parse action from args: screenshot / click / type / goto
        action = "screenshot"
        url = ""
        full_page = False
        wait_ms = 1500
        for line in args.splitlines():
            line = line.strip()
            if line.startswith("url:"):
                url = line[4:].strip()
            elif line.startswith("full_page:"):
                full_page = line[10:].strip().lower() in ("true", "yes", "1")
            elif line.startswith("wait_ms:"):
                try:
                    wait_ms = int(line[8:].strip())
                except ValueError:
                    pass
            elif line.startswith("action:"):
                action = line[7:].strip()
        if not url and action == "screenshot":
            return "[internet ERROR: url не указан]"
        try:
            import urllib.request as _req
            import json as _json
            payload = _json.dumps({
                "url": url,
                "full_page": full_page,
                "wait_ms": wait_ms,
            }).encode()
            req = _req.Request(
                "http://127.0.0.1:5006/api/v1/screenshot",
                data=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with _req.urlopen(req, timeout=35) as resp:
                raw = resp.read()
            # Save PNG
            import tempfile, os
            tmp = tempfile.mktemp(suffix=".png", prefix="fc_screenshot_")
            with open(tmp, "wb") as f:
                f.write(raw)
            return f"[internet: скриншот готов → {tmp} ({len(raw)} байт)]\n<IMAGE:path={tmp}>"
        except Exception as e:
            err_str = str(e)
            if "ConnectionRefused" in err_str or "Connection refused" in err_str:
                return "[internet ERROR: FavoriteChrome не отвечает на 127.0.0.1:5006. Запусти: python server.py]"
            if "401" in err_str:
                return "[internet ERROR: токен отвязан. Привяжи снова через /skills internet on]"
            return f"[internet ERROR: {e}]"

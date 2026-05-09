"""
favorite/skills/fetch_url.py — Fetch URL content skill (ISkill wrapper).
"""
import re
import urllib.request
from .base import ISkill


class FetchUrlSkill(ISkill):
    @property
    def name(self) -> str:
        return "fetch_url"

    def run(self, args: str, ctx=None, cfg=None) -> str:
        url = (args or "").strip()
        if not url:
            return "[fetch_url ERROR: URL не указан]"
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FavoriteCLI/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                # Try utf-8, then latin-1
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="replace")

            # Strip HTML tags for readability
            text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
            text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s{3,}", "\n\n", text)
            text = text.strip()

            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...[обрезано]"
            return f"[URL: {url}]\n{text}"
        except Exception as e:
            return f"[fetch_url ERROR: {e}]"

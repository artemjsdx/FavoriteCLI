"""
favorite/commands/web_cmd.py — /web and /fetch commands.
"""
import urllib.request
import urllib.parse
import re
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()


def _duckduckgo_search(query: str) -> str:
    try:
        q = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.S)
        links = re.findall(r'href="(https?://[^"&]+)"', html)
        results = []
        for i, (t, s) in enumerate(zip(titles[:5], snippets[:5])):
            title = re.sub(r'<[^>]+>', '', t).strip()
            snip = re.sub(r'<[^>]+>', '', s).strip()
            link = links[i] if i < len(links) else ""
            results.append(f"{i+1}. {title}\n   {snip}\n   {link}")
        return "\n\n".join(results) if results else "(нет результатов)"
    except Exception as e:
        return f"Ошибка поиска: {e}"


def _fetch_url(url: str, max_chars: int = 4000) -> str:
    try:
        req = urllib.request.Request(url.strip(), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.S)
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.S)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [обрезано: показано {max_chars} из {len(text)} символов]"
        return text
    except Exception as e:
        return f"Ошибка загрузки: {e}"


class WebCommand(ICommand):
    name = "/web"
    description = "Поиск в интернете (DuckDuckGo)"
    priority = 46

    def execute(self, args: str, ctx: CommandContext) -> None:
        query = args.strip()
        if not query:
            console.print("  [dim]Использование: /web <запрос>[/dim]")
            return
        console.print()
        console.print(f"  [bold #ff8c00]~[/bold #ff8c00] [dim]Поиск: {escape(query[:60])}[/dim]")
        result = _duckduckgo_search(query)
        console.print()
        console.print(result)
        console.print()


class FetchCommand(ICommand):
    name = "/fetch"
    description = "Загрузить страницу по URL"
    priority = 47

    def execute(self, args: str, ctx: CommandContext) -> None:
        url = args.strip()
        if not url:
            console.print("  [dim]Использование: /fetch <url>[/dim]")
            return
        console.print()
        console.print(f"  [bold #ff8c00]~[/bold #ff8c00] [dim]Fetch: {escape(url[:80])}[/dim]")
        result = _fetch_url(url)
        console.print()
        console.print(result[:2000])
        if len(result) > 2000:
            console.print(f"  [dim]... +{len(result)-2000} символов[/dim]")
        console.print()

"""
favorite/commands/ide_cmd.py — /ide command (§44.2 IDE mode).
Launches FastAPI WebSocket server + cloudflared tunnel for browser-based IDE.
"""
import json
import subprocess
import secrets
import threading
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()

_IDE_STATE: dict = {
    "running": False,
    "url": None,
    "token": None,
    "port": 8080,
    "server_proc": None,
    "cloudflared_proc": None,
}


def _get_free_port(default: int = 8080) -> int:
    import socket
    for port in range(default, default + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return default


def _start_cloudflared(port: int) -> str | None:
    """Start cloudflared tunnel. Returns public URL or None."""
    import re
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        _IDE_STATE["cloudflared_proc"] = proc
        for _ in range(30):
            import time; time.sleep(0.5)
            err_line = proc.stderr.readline()
            m = re.search(r"https://[\w-]+\.trycloudflare\.com", err_line)
            if m:
                return m.group(0)
    except FileNotFoundError:
        console.print("  [red]cloudflared не найден. Установи: pkg install cloudflared[/red]")
    except Exception as e:
        console.print(f"  [red]cloudflared error: {e}[/red]")
    return None


def _start_ide_server(port: int, auth_token: str, workdir: str) -> None:
    """Start FastAPI IDE server in a daemon thread."""
    def _server_thread():
        try:
            import uvicorn
            from favorite.ide_server import create_app
            app = create_app(auth_token=auth_token, workdir=workdir)
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
        except ImportError:
            console.print("  [red]FastAPI/uvicorn не установлены. Запусти: pip install fastapi uvicorn[standard][/red]")
        except Exception as e:
            console.print(f"  [red]IDE server error: {e}[/red]")
        finally:
            _IDE_STATE["running"] = False

    t = threading.Thread(target=_server_thread, daemon=True)
    t.start()


class IdeCommand(ICommand):
    name = "/ide"
    description = "Запустить IDE-режим (браузерный интерфейс) через cloudflared (§44)"
    priority = 85

    def execute(self, args: str, ctx: CommandContext) -> None:
        args = (args or "").strip().lower()

        if args == "stop":
            self._stop()
            return

        if args == "status":
            if _IDE_STATE["running"]:
                url = _IDE_STATE.get("url", "неизвестно")
                console.print(f"  [bold]IDE запущен:[/bold] {escape(url or 'локальный')}")
            else:
                console.print("  [dim]IDE не запущен[/dim]")
            return

        if _IDE_STATE["running"]:
            url = _IDE_STATE.get("url", "")
            console.print(f"  [dim]IDE уже запущен:[/dim] {escape(url)}")
            console.print("  [dim]Остановить: /ide stop[/dim]")
            return

        # Start IDE
        port = _get_free_port(8080)
        auth_token = secrets.token_hex(16)
        _IDE_STATE["port"] = port
        _IDE_STATE["token"] = auth_token
        _IDE_STATE["running"] = True

        console.print(f"  [dim #666666]Запускаю IDE-сервер на порту {port}...[/dim #666666]")
        _start_ide_server(port, auth_token, ctx.workdir)

        import time; time.sleep(1)

        console.print("  [dim #666666]Открываю cloudflare туннель...[/dim #666666]")
        public_url = _start_cloudflared(port)

        if public_url:
            full_url = f"{public_url}/?token={auth_token}"
            _IDE_STATE["url"] = full_url
            console.print(f"  [bold]✓ IDE готов:[/bold]")
            console.print(f"  [link={escape(full_url)}]{escape(full_url)}[/link]")
            console.print("  [dim]Остановить: /ide stop[/dim]")
            # Save to config
            try:
                ide_cfg = Path(ctx.workdir) / "config" / "ide_session.json"
                ide_cfg.write_text(
                    json.dumps({"url": full_url, "port": port}, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
            except Exception:
                pass
        else:
            local_url = f"http://localhost:{port}/?token={auth_token}"
            _IDE_STATE["url"] = local_url
            console.print(f"  [yellow]⚠ Cloudflare туннель не запущен. IDE доступен локально:[/yellow]")
            console.print(f"  {escape(local_url)}")

    def _stop(self) -> None:
        if not _IDE_STATE["running"]:
            console.print("  [dim]IDE не запущен[/dim]")
            return
        _IDE_STATE["running"] = False
        cf = _IDE_STATE.get("cloudflared_proc")
        if cf:
            try: cf.terminate()
            except Exception: pass
        _IDE_STATE.update({"url": None, "token": None, "server_proc": None, "cloudflared_proc": None})
        console.print("  [dim #666666]IDE остановлен[/dim #666666]")

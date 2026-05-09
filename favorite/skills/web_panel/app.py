"""
favorite/skills/web_panel/app.py
FastAPI application for FavoriteCLI web dashboard.
"""
import json
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False


def create_app(workdir: str = ".") -> "FastAPI":
    if not _HAS_FASTAPI:
        raise ImportError("fastapi not installed")

    app = FastAPI(title="FavoriteCLI Dashboard", version="1.0.0")
    _workdir = Path(workdir)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        sessions = []
        sess_dir = _workdir / "sessions"
        if sess_dir.exists():
            for d in sorted(sess_dir.iterdir(), reverse=True):
                if d.is_dir():
                    info = {"id": d.name, "created": "?", "messages": 0}
                    hist = d / "history.json"
                    if hist.exists():
                        try:
                            data = json.loads(hist.read_text(encoding="utf-8"))
                            info["messages"] = len(data) if isinstance(data, list) else 0
                        except Exception:
                            pass
                    sessions.append(info)

        sessions_html = "".join(
            f'<tr><td><a href="/session/{s["id"]}">{s["id"]}</a></td>'
            f'<td>{s["messages"]}</td></tr>'
            for s in sessions[:20]
        )

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>FavoriteCLI Dashboard</title>
<style>
  body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 2rem; }}
  h1 {{ color: #ff8c00; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #333; padding: 0.5rem 1rem; text-align: left; }}
  th {{ background: #0f3460; color: #ff8c00; }}
  a {{ color: #4fc3f7; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .badge {{ background: #ff8c00; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }}
</style>
</head>
<body>
<h1>🔥 FavoriteCLI Dashboard</h1>
<p>Workdir: <code>{workdir}</code> &nbsp;|&nbsp; <span class="badge">{len(sessions)} сессий</span></p>
<h2>Сессии</h2>
<table>
<tr><th>ID сессии</th><th>Сообщений</th></tr>
{sessions_html or "<tr><td colspan='2'>Сессий нет</td></tr>"}
</table>
<hr>
<p style="color:#555">FavoriteCLI Web Panel — обновляй страницу для актуальных данных</p>
</body>
</html>"""
        return HTMLResponse(content=html)

    @app.get("/api/sessions")
    async def api_sessions():
        sessions = []
        sess_dir = _workdir / "sessions"
        if sess_dir.exists():
            for d in sorted(sess_dir.iterdir(), reverse=True):
                if d.is_dir():
                    hist = d / "history.json"
                    msg_count = 0
                    if hist.exists():
                        try:
                            data = json.loads(hist.read_text(encoding="utf-8"))
                            msg_count = len(data) if isinstance(data, list) else 0
                        except Exception:
                            pass
                    sessions.append({"id": d.name, "messages": msg_count})
        return JSONResponse({"sessions": sessions[:50]})

    @app.get("/session/{session_id}", response_class=HTMLResponse)
    async def session_detail(session_id: str):
        sess_dir = _workdir / "sessions" / session_id
        history = []
        hist_file = sess_dir / "history.json"
        if hist_file.exists():
            try:
                history = json.loads(hist_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        plan = ""
        plan_file = sess_dir / "plan.txt"
        if plan_file.exists():
            plan = plan_file.read_text(encoding="utf-8")

        msgs_html = ""
        for m in history[-30:]:
            role = m.get("role", "?")
            content = str(m.get("content", ""))[:500].replace("<", "&lt;").replace(">", "&gt;")
            color = "#4fc3f7" if role == "user" else "#ff8c00"
            msgs_html += f'<div style="margin:0.5rem 0;border-left:3px solid {color};padding-left:0.5rem"><b style="color:{color}">{role}</b><pre style="margin:0;white-space:pre-wrap">{content}</pre></div>'

        plan_html = f"<h2>План</h2><pre>{plan[:2000].replace('<','&lt;')}</pre>" if plan else ""

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Сессия {session_id}</title>
<style>
  body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 2rem; }}
  h1,h2 {{ color: #ff8c00; }}
  pre {{ background:#0f0f1a; padding:0.5rem; border-radius:4px; overflow:auto; }}
  a {{ color: #4fc3f7; }}
</style>
</head>
<body>
<h1>Сессия: {session_id}</h1>
<a href="/">← назад</a>
{plan_html}
<h2>История ({len(history)} сообщений, показаны последние 30)</h2>
{msgs_html or "<p>История пуста</p>"}
</body>
</html>"""
        return HTMLResponse(content=html)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "workdir": workdir, "ts": datetime.now().isoformat()}

    return app

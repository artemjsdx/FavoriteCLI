"""
favorite/ide_server.py — FastAPI IDE server (§44.2).
WebSocket + REST backend for the browser-based IDE mode.
Run via /ide command using uvicorn.
"""
import json
import time
import secrets
from pathlib import Path
from typing import Any


def create_app(auth_token: str, workdir: str):
    """Create and return FastAPI app for IDE server."""
    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    except ImportError:
        raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn[standard]")

    app = FastAPI(title="FavoriteCLI IDE", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _ws_clients: list[WebSocket] = []

    async def verify_token(token: str = None) -> bool:
        return token == auth_token

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "workdir": workdir, "ts": time.time()}

    @app.get("/api/files")
    async def list_files(path: str = ".", token: str = None):
        if token != auth_token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        base = Path(workdir) / path
        if not base.exists() or not base.is_dir():
            raise HTTPException(status_code=404, detail="Not found")
        entries = []
        for item in sorted(base.iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return {"path": str(path), "entries": entries}

    @app.get("/api/file")
    async def read_file(path: str, token: str = None):
        if token != auth_token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        fp = Path(workdir) / path
        if not fp.exists() or not fp.is_file():
            raise HTTPException(status_code=404, detail="Not found")
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
            return {"path": str(path), "content": content}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        token_param = ws.query_params.get("token", "")
        if token_param != auth_token:
            await ws.close(code=4001)
            return
        await ws.accept()
        _ws_clients.append(ws)
        try:
            while True:
                data = await ws.receive_text()
                event = json.loads(data)
                # Echo back for now (full integration in future)
                await ws.send_text(json.dumps({
                    "type": "ack",
                    "received": event.get("type", "unknown"),
                }))
        except WebSocketDisconnect:
            pass
        finally:
            _ws_clients.remove(ws)

    return app

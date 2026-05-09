"""FastAPI server for FavoriteCLI on port 8080"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="FavoriteCLI Server", version="1.0.0")

@app.get("/")
async def index():
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>FavoriteCLI Server</title>
<style>
  body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 2rem; }}
  h1 {{ color: #ff8c00; }}
  .status {{ padding: 1rem; background: #0f3460; border-radius: 8px; margin-top: 1rem; }}
  .uptime {{ color: #5fd7af; }}
</style>
</head>
<body>
<h1>🔥 FavoriteCLI Server</h1>
<div class="status">
  <strong>Status:</strong> <span class="uptime">RUNNING</span><br>
  <strong>Port:</strong> 8080<br>
  <strong>Start time:</strong> {os.popen('date').read().strip()}
</div>
<hr>
<p>Server is working correctly.</p>
</body>
</html>""")

@app.get("/health")
async def health():
    return {"status": "ok", "port": 8080, "message": "FavoriteCLI server is running"}

@app.get("/api/status")
async def status():
    import platform
    return {
        "running": True,
        "port": 8080,
        "platform": platform.system(),
        "python_version": platform.python_version()
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("FavoriteCLI Server starting on port 8080...")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8080)

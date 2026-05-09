import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent / "sessions"


class SessionManager:
  def __init__(self):
      _BASE.mkdir(parents=True, exist_ok=True)

  def create_session(self, workdir: str = "", title: str = "") -> str:
      sid = str(uuid.uuid4())
      meta = {
          "session_id": sid,
          "title": title or "Новая сессия",
          "created_at": datetime.now(timezone.utc).isoformat(),
          "workdir": workdir,
          "leading_main_agent": "",
          "agents": [],
          "stats": {
              "total_tokens": 0,
              "requests": 0,
              "start_time": datetime.now(timezone.utc).isoformat()
          }
      }
      session_dir = _BASE / sid
      session_dir.mkdir(parents=True, exist_ok=True)
      (session_dir / "meta.json").write_text(
          json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
      )
      (session_dir / "history.jsonl").write_text("", encoding="utf-8")
      return sid

  def update_stats(self, session_id: str, tokens: int) -> None:
      meta_file = _BASE / session_id / "meta.json"
      if meta_file.exists():
          try:
              meta = json.loads(meta_file.read_text(encoding="utf-8"))
              if "stats" not in meta:
                  meta["stats"] = {
                      "total_tokens": 0,
                      "requests": 0,
                      "start_time": meta.get("created_at", datetime.now(timezone.utc).isoformat())
                  }
              meta["stats"]["total_tokens"] += tokens
              meta["stats"]["requests"] += 1
              meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
          except Exception:
              pass

  def list_sessions(self) -> list[dict]:
      result = []
      for p in sorted(_BASE.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
          meta_file = p / "meta.json"
          if meta_file.exists():
              try:
                  result.append(json.loads(meta_file.read_text(encoding="utf-8")))
              except Exception:
                  pass
      return result

  def get_session(self, session_id: str) -> dict | None:
      meta_file = _BASE / session_id / "meta.json"
      if not meta_file.exists():
          return None
      return json.loads(meta_file.read_text(encoding="utf-8"))

  def append_history(self, session_id: str, event: dict) -> None:
      history_file = _BASE / session_id / "history.jsonl"
      with open(history_file, "a", encoding="utf-8") as f:
          f.write(json.dumps(event, ensure_ascii=False) + "\n")

  def load_history(self, session_id: str) -> list[dict]:
      history_file = _BASE / session_id / "history.jsonl"
      if not history_file.exists():
          return []
      result = []
      for line in history_file.read_text(encoding="utf-8").splitlines():
          line = line.strip()
          if line:
              try:
                  result.append(json.loads(line))
              except Exception:
                  pass
      return result

  def clear_history(self, session_id: str) -> None:
      history_file = _BASE / session_id / "history.jsonl"
      if history_file.exists():
          history_file.write_text("", encoding="utf-8")

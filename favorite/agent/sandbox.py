"""
favorite/agent/sandbox.py — Sub-agent sandbox manager (§19.5).

Creates isolated per-sub-agent workdirs so their file ops never touch
the main project tree. Sandbox is opt-in — disabled by default.

Config: config/modules.json → {"sub_agent_sandbox": true}
Tag:    <SUB_AGENT:role="coder" sandbox="true">task</SUB_AGENT>
"""
import shutil
import uuid
from pathlib import Path
from typing import Optional

_SANDBOX_ROOT = "sandboxes"   # relative to session workdir


def make_sandbox(parent_workdir: str, session_id: str, agent_label: str = "") -> Path:
  """
  Create an isolated sandbox workdir for a sub-agent.
  Returns the sandbox path.  Caller is responsible for cleanup.
  """
  sid   = str(uuid.uuid4())[:8]
  label = (agent_label or "sub").replace("/", "_").replace("\\", "_")[:20]
  name  = f"{label}_{sid}"
  sand  = Path(parent_workdir) / "sessions" / session_id / _SANDBOX_ROOT / name
  sand.mkdir(parents=True, exist_ok=True)
  # Seed with a minimal README so the agent knows where it is
  (sand / ".sandbox_info").write_text(
      f"sandbox={name}\nparent={parent_workdir}\nsession={session_id}\n",
      encoding="utf-8",
  )
  return sand


def cleanup_sandbox(sandbox_path: Path) -> None:
  """Remove a sandbox directory tree. Silent on errors."""
  try:
      if sandbox_path.exists():
          shutil.rmtree(sandbox_path, ignore_errors=True)
  except Exception:
      pass


def list_sandboxes(parent_workdir: str, session_id: str) -> list[Path]:
  """List all sandbox dirs for the current session."""
  root = Path(parent_workdir) / "sessions" / session_id / _SANDBOX_ROOT
  if not root.exists():
      return []
  return sorted(root.iterdir())


def is_sandbox_enabled_globally(cfg=None) -> bool:
  """
  Check if sandbox is enabled globally via config/modules.json.
  Returns False if not configured (opt-in).
  """
  try:
      import json
      from pathlib import Path as _P
      mod_file = _P("config/modules.json")
      if mod_file.exists():
          data = json.loads(mod_file.read_text(encoding="utf-8"))
          return bool(data.get("sub_agent_sandbox", False))
  except Exception:
      pass
  return False

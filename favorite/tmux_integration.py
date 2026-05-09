"""
favorite/tmux_integration.py — tmux integration (§36).
Start/stop/attach tmux sessions for workers and long-running tasks.
"""
import subprocess
from typing import Optional


def is_tmux_available() -> bool:
    try:
        r = subprocess.run(["which", "tmux"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def session_exists(session_name: str) -> bool:
    try:
        r = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def new_session(session_name: str, command: str, cwd: Optional[str] = None) -> bool:
    """Start a new tmux session running command in background."""
    try:
        cmd = ["tmux", "new-session", "-d", "-s", session_name]
        if cwd:
            cmd += ["-c", cwd]
        cmd += [command]
        r = subprocess.run(cmd, capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def kill_session(session_name: str) -> bool:
    try:
        r = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def send_keys(session_name: str, keys: str) -> bool:
    """Send keystrokes to a tmux session."""
    try:
        r = subprocess.run(
            ["tmux", "send-keys", "-t", session_name, keys, "Enter"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def list_sessions() -> list[dict]:
    """List all tmux sessions with their info."""
    try:
        r = subprocess.run(
            ["tmux", "list-sessions", "-F",
             "#{session_name}:#{session_windows}:#{session_created}:#{session_attached}"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode != 0:
            return []
        sessions = []
        for line in r.stdout.strip().splitlines():
            parts = line.split(":", 3)
            if len(parts) >= 4:
                sessions.append({
                    "name": parts[0],
                    "windows": parts[1],
                    "created": parts[2],
                    "attached": parts[3] == "1",
                })
        return sessions
    except Exception:
        return []


def capture_output(session_name: str, lines: int = 50) -> str:
    """Capture last N lines of output from a tmux session."""
    try:
        r = subprocess.run(
            ["tmux", "capture-pane", "-pt", session_name, "-S", str(-lines)],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def start_in_tmux_or_background(
    session_name: str,
    command: str,
    cwd: Optional[str] = None,
    prefer_tmux: bool = True,
) -> dict:
    """
    Start a command in tmux if available, else in background subprocess.
    Returns {"method": "tmux"|"subprocess", "pid": int|None, "session": str|None}
    """
    if prefer_tmux and is_tmux_available():
        if new_session(session_name, command, cwd=cwd):
            return {"method": "tmux", "pid": None, "session": session_name}
    import subprocess as sp
    import shlex
    proc = sp.Popen(shlex.split(command), cwd=cwd, start_new_session=True)
    return {"method": "subprocess", "pid": proc.pid, "session": None}

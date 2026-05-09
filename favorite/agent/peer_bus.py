"""
favorite/agent/peer_bus.py — Peer-traffic bus (§18.2).

File-based message bus for inter-agent communication.
Main agents in the same session send/receive typed messages via shared JSON files.

Tag syntax (used by agents in responses):
  <ASK_PEER:to="agent-2" timeout="15">your question here</ASK_PEER>
  <DELEGATE_PEER:to="agent-1" role="coder">full task description</DELEGATE_PEER>
  <NOTIFY_PEER:to="agent-3" event="done">optional payload</NOTIFY_PEER>

Bus layout (per session):
  sessions/<id>/peer_bus/
    inbox_<agent_id>.jsonl   — append-only inbox for each agent
    outbox_<agent_id>.jsonl  — sent messages log
    pending_<msg_id>.json    — pending ASK_PEER waiting for reply
"""
import json
import uuid
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


_BUS_DIR   = "peer_bus"
_MAIN_ID   = "main-1"          # default main agent id
_TIMEOUT   = 15                # seconds to wait for ASK_PEER reply
_MAX_INBOX = 200               # max messages kept in inbox per agent


# ── Public send functions ─────────────────────────────────────────────────────

def ask_peer(
    to: str, question: str,
    from_id: str, session_id: str, workdir: str,
    cfg=None, ctx=None,
    timeout: int = _TIMEOUT,
) -> str:
    """
    Send a question to a peer agent and wait for a reply.
    Blocks up to *timeout* seconds. Returns reply text or timeout message.
    """
    msg_id = _new_msg_id()
    _send(
        to=to, from_id=from_id,
        kind="ask", msg_id=msg_id,
        payload={"question": question},
        session_id=session_id, workdir=workdir,
    )
    _show_sent("ASK_PEER", to, question[:80])

    # Spawn sub-agent to answer if no live agent is polling
    reply_event = threading.Event()
    reply_box: list[str] = []

    def _auto_reply():
        try:
            from .sub_agent import run_sub_agent
            task = (
                f"You are agent {to}. Another agent ({from_id}) asks:\n\n"
                f"{question}\n\n"
                f"Give a concise, direct answer. msg_id={msg_id}"
            )
            result = run_sub_agent("analyst", task, cfg, ctx=ctx)
            reply_box.append(result.strip())
        except Exception as e:
            reply_box.append(f"[error: {e}]")
        finally:
            # Write reply back to sender inbox
            _send(
                to=from_id, from_id=to,
                kind="reply", msg_id=_new_msg_id(),
                payload={"reply_to": msg_id, "text": reply_box[0] if reply_box else "[no reply]"},
                session_id=session_id, workdir=workdir,
            )
            reply_event.set()

    t = threading.Thread(target=_auto_reply, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if reply_box:
        _show_received("ASK_PEER", to, reply_box[0][:120])
        return f"[REPLY from {to}] {reply_box[0]}"
    return f"[ASK_PEER timeout after {timeout}s — no reply from {to}]"


def delegate_peer(
    to: str, task: str, role: str,
    from_id: str, session_id: str, workdir: str,
    cfg=None, ctx=None,
) -> str:
    """
    Delegate a task to a peer agent (fire-and-wait, up to 60s).
    The peer sub-agent executes the full task and returns its result.
    """
    msg_id = _new_msg_id()
    _send(
        to=to, from_id=from_id,
        kind="delegate", msg_id=msg_id,
        payload={"task": task, "role": role},
        session_id=session_id, workdir=workdir,
    )
    _show_sent("DELEGATE_PEER", to, f"role={role} | {task[:60]}")

    result_box: list[str] = []

    def _run_delegated():
        try:
            from .sub_agent import run_sub_agent
            result = run_sub_agent(role or "analyst", task, cfg, ctx=ctx)
            result_box.append(result.strip())
        except Exception as e:
            result_box.append(f"[delegation error: {e}]")
        finally:
            _send(
                to=from_id, from_id=to,
                kind="delegate_result", msg_id=_new_msg_id(),
                payload={"reply_to": msg_id, "result": result_box[0] if result_box else "[empty]"},
                session_id=session_id, workdir=workdir,
            )

    t = threading.Thread(target=_run_delegated, daemon=True)
    t.start()
    t.join(timeout=60)

    if result_box:
        _show_received("DELEGATE_PEER", to, result_box[0][:120])
        return f"[DELEGATE RESULT from {to} (role={role})]\n{result_box[0]}"
    return f"[DELEGATE_PEER timeout — {to} did not complete within 60s]"


def notify_peer(
    to: str, event: str, payload_text: str,
    from_id: str, session_id: str, workdir: str,
) -> str:
    """
    Fire-and-forget notification. Does not wait for reply.
    """
    msg_id = _new_msg_id()
    _send(
        to=to, from_id=from_id,
        kind="notify", msg_id=msg_id,
        payload={"event": event, "text": payload_text},
        session_id=session_id, workdir=workdir,
    )
    _show_sent("NOTIFY_PEER", to, f"event={event} | {payload_text[:60]}")
    return f"[NOTIFY_PEER → {to} | event={event}]"


# ── Inbox read functions ───────────────────────────────────────────────────────

def read_inbox(agent_id: str, session_id: str, workdir: str,
               limit: int = 10, unread_only: bool = True) -> list[dict]:
    """Read messages from an agent's inbox."""
    inbox_path = _bus_dir(workdir, session_id) / f"inbox_{agent_id}.jsonl"
    if not inbox_path.exists():
        return []
    messages: list[dict] = []
    try:
        for line in inbox_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    msg = json.loads(line)
                    if not unread_only or not msg.get("read"):
                        messages.append(msg)
                except Exception:
                    pass
    except Exception:
        pass
    return messages[-limit:]


def mark_read(agent_id: str, msg_id: str, session_id: str, workdir: str) -> None:
    """Mark a message as read (rewrites inbox file)."""
    inbox_path = _bus_dir(workdir, session_id) / f"inbox_{agent_id}.jsonl"
    if not inbox_path.exists():
        return
    try:
        lines = inbox_path.read_text(encoding="utf-8").splitlines()
        updated = []
        for line in lines:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                if msg.get("msg_id") == msg_id:
                    msg["read"] = True
                updated.append(json.dumps(msg, ensure_ascii=False))
            except Exception:
                updated.append(line)
        inbox_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    except Exception:
        pass


def get_bus_status(session_id: str, workdir: str) -> dict:
    """Return bus status: message counts per agent."""
    bus = _bus_dir(workdir, session_id)
    status: dict = {}
    if not bus.exists():
        return status
    for f in bus.glob("inbox_*.jsonl"):
        agent_id = f.stem.replace("inbox_", "")
        try:
            lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
            unread = sum(1 for l in lines if not json.loads(l).get("read", False))
            status[agent_id] = {"total": len(lines), "unread": unread}
        except Exception:
            status[agent_id] = {"total": 0, "unread": 0}
    return status


# ── Internal helpers ──────────────────────────────────────────────────────────

def _bus_dir(workdir: str, session_id: str) -> Path:
    d = Path(workdir) / "sessions" / session_id / _BUS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _send(to: str, from_id: str, kind: str, msg_id: str,
          payload: dict, session_id: str, workdir: str) -> None:
    bus = _bus_dir(workdir, session_id)
    msg = {
        "msg_id":   msg_id,
        "kind":     kind,
        "from":     from_id,
        "to":       to,
        "payload":  payload,
        "ts":       datetime.utcnow().isoformat(),
        "read":     False,
    }
    # Append to recipient inbox
    inbox = bus / f"inbox_{to}.jsonl"
    with open(inbox, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    # Append to sender outbox
    outbox = bus / f"outbox_{from_id}.jsonl"
    with open(outbox, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")


def _new_msg_id() -> str:
    return str(uuid.uuid4())[:8]


def _show_sent(kind: str, to: str, preview: str) -> None:
    from rich.console import Console
    from rich.markup import escape
    Console().print(
        f"  [bold #ff8c00]→[/bold #ff8c00] [dim]{kind}[/dim]"
        f" [dim #555555]to[/dim #555555] [cyan]{to}[/cyan]"
        f"  [dim #444444]{escape(preview)}[/dim #444444]"
    )


def _show_received(kind: str, from_id: str, preview: str) -> None:
    from rich.console import Console
    from rich.markup import escape
    Console().print(
        f"  [bold #5fd7af]←[/bold #5fd7af] [dim]{kind}[/dim]"
        f" [dim #555555]from[/dim #555555] [cyan]{from_id}[/cyan]"
        f"  [dim #888888]{escape(preview)}[/dim #888888]"
    )

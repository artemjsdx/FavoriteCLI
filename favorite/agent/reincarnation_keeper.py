"""
favorite/agent/reincarnation_keeper.py — §18.5 Full reincarnation protocol.

6-step protocol:
  1. Write rescue note (REINCARNATE tag)
  2. Select keeper (agent with most context overlap)
  3. NOTIFY_PEER keeper with BRIEF
  4. Reset dying agent's context
  5. New agent receives BRIEF from keeper
  6. Log to sessions/<id>/history.jsonl
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional, List

from .crew import get_crew, MainAgent
from .cross_chat import get_bus


_ROOT = Path(__file__).resolve().parent.parent.parent


def select_keeper(dying_agent_name: str, brief_keywords: List[str]) -> Optional[MainAgent]:
    """
    Select the best keeper for the dying agent's memory.
    Strategy: active agent with most keyword matches in its bio.
    Fallback: first active agent that is not dying.
    """
    crew = get_crew()
    actives = [a for a in crew.list_active() if a.name != dying_agent_name]
    if not actives:
        return None

    if not brief_keywords:
        return actives[0]

    def score(agent: MainAgent) -> int:
        text = (agent.bio + " " + agent.role).lower()
        return sum(1 for kw in brief_keywords if kw.lower() in text)

    return max(actives, key=score)


def write_rescue_note(session_id: str, dying_agent: str, brief: str) -> Path:
    """Write a rescue note to sessions/<id>/reincarnation_notes.jsonl"""
    notes_dir = _ROOT / "sessions" / session_id
    notes_dir.mkdir(parents=True, exist_ok=True)
    notes_file = notes_dir / "reincarnation_notes.jsonl"
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "agent": dying_agent,
        "brief": brief,
    }
    with notes_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return notes_file


def log_to_history(session_id: str, event: dict) -> None:
    """Append event to sessions/<id>/history.jsonl"""
    hist = _ROOT / "sessions" / session_id / "history.jsonl"
    hist.parent.mkdir(parents=True, exist_ok=True)
    with hist.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}, ensure_ascii=False) + "\n")


def full_reincarnation_protocol(
    session_id: str,
    dying_agent_name: str,
    brief: str,
    reset_callback=None,
) -> dict:
    """
    Execute all 6 reincarnation steps.
    reset_callback(agent_name) — clears the agent's context externally.
    Returns summary dict.
    """
    crew = get_crew()
    bus = get_bus()

    # Step 1: write rescue note
    note_path = write_rescue_note(session_id, dying_agent_name, brief)

    # Step 2: select keeper
    brief_keywords = [w for w in brief.split() if len(w) > 4][:20]
    keeper = select_keeper(dying_agent_name, brief_keywords)
    keeper_name = keeper.name if keeper else "none"

    # Step 3: NOTIFY_PEER keeper with BRIEF
    if keeper:
        bus.send(
            msg_type="brief",
            from_agent=dying_agent_name,
            to_agent=keeper_name,
            content=f"[НАСЛЕДИЕ ОТ {dying_agent_name}]\n{brief}",
            ttl=3600,
        )

    # Step 4: reset dying agent context
    if reset_callback:
        try:
            reset_callback(dying_agent_name)
        except Exception as e:
            log_to_history(session_id, {"type": "reincarnate_reset_error", "agent": dying_agent_name, "error": str(e)})

    # Step 6: log
    log_to_history(session_id, {
        "type": "reincarnate",
        "agent": dying_agent_name,
        "keeper": keeper_name,
        "brief_len": len(brief),
        "note_path": str(note_path),
    })

    return {
        "status": "ok",
        "dying_agent": dying_agent_name,
        "keeper": keeper_name,
        "note_path": str(note_path),
        "brief_sent": keeper is not None,
    }

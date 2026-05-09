"""
favorite/agent/cross_chat.py — §18 Inter-agent dialogue bus.

Implements BRIEF, VOTE, ASK_PEER cross-agent message routing
when multiple main agents are active.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable

from .crew import get_crew


@dataclass
class CrossMessage:
    msg_id: str
    msg_type: str          # "brief" | "ask" | "reply" | "vote_call" | "vote_cast"
    from_agent: str
    to_agent: str          # "*" = broadcast
    content: str
    ts: float = field(default_factory=time.time)
    ttl: float = 300.0     # seconds; 0 = no expiry
    replied: bool = False


class CrossChatBus:
    """
    In-memory inter-agent message bus.
    Agents push messages → recipients poll via get_messages().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._messages: Dict[str, CrossMessage] = {}
        self._subscribers: Dict[str, List[Callable]] = {}

    def send(self, msg_type: str, from_agent: str, to_agent: str, content: str,
             ttl: float = 300.0) -> str:
        msg_id = uuid.uuid4().hex[:12]
        msg = CrossMessage(msg_id=msg_id, msg_type=msg_type,
                           from_agent=from_agent, to_agent=to_agent,
                           content=content, ttl=ttl)
        with self._lock:
            self._messages[msg_id] = msg
            self._notify(to_agent, msg)
        return msg_id

    def reply(self, original_id: str, from_agent: str, content: str) -> Optional[str]:
        with self._lock:
            orig = self._messages.get(original_id)
            if not orig:
                return None
            orig.replied = True
        return self.send("reply", from_agent, orig.from_agent, content)

    def get_messages(self, agent_name: str, unread_only: bool = True) -> List[CrossMessage]:
        now = time.time()
        with self._lock:
            msgs = []
            for m in self._messages.values():
                if m.ttl > 0 and (now - m.ts) > m.ttl:
                    continue
                if m.to_agent not in (agent_name, "*"):
                    continue
                if unread_only and m.replied:
                    continue
                msgs.append(m)
        return sorted(msgs, key=lambda m: m.ts)

    def _notify(self, agent_name: str, msg: CrossMessage) -> None:
        for cb in self._subscribers.get(agent_name, []):
            try:
                cb(msg)
            except Exception:
                pass
        for cb in self._subscribers.get("*", []):
            try:
                cb(msg)
            except Exception:
                pass

    def subscribe(self, agent_name: str, callback: Callable) -> None:
        self._subscribers.setdefault(agent_name, []).append(callback)

    def cleanup_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, m in self._messages.items()
                       if m.ttl > 0 and (now - m.ts) > m.ttl]
            for k in expired:
                del self._messages[k]
        return len(expired)

    def brief_family(self, from_agent: str, brief_text: str) -> List[str]:
        """Broadcast a BRIEF to all active agents except sender."""
        crew = get_crew()
        ids = []
        for agent in crew.list_active():
            if agent.name != from_agent:
                ids.append(self.send("brief", from_agent, agent.name, brief_text))
        return ids

    def pending_for(self, agent_name: str) -> int:
        return len(self.get_messages(agent_name, unread_only=True))


# Singleton
_bus: Optional[CrossChatBus] = None


def get_bus() -> CrossChatBus:
    global _bus
    if _bus is None:
        _bus = CrossChatBus()
    return _bus

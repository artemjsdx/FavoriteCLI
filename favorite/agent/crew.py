"""
favorite/agent/crew.py — §18 Multi-main crew management.

Manages a «family» of main agents: list, add, remove, activate.
Each main agent has: name, model_id, provider, api_key, role, bio.
Persistent state in config/agents_config.json.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENTS_CFG = _ROOT / "config" / "agents_config.json"
_AGENTS_DIR = _ROOT / "agents"


@dataclass
class MainAgent:
    id: str
    name: str                     # «main-1», «sub-critic», etc.
    provider: str                 # "favorite" | "openrouter"
    model_id: str
    api_key: str
    role: str = "general"
    bio: str = ""
    active: bool = True
    is_leading: bool = False
    ctx_used_pct: float = 0.0     # обновляется при каждом вызове

    @classmethod
    def from_dict(cls, d: dict) -> "MainAgent":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})

    def to_dict(self) -> dict:
        return asdict(self)


class Crew:
    """
    Family of main agents.
    Thread-safe read. Write operations save immediately.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, MainAgent] = {}
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if _AGENTS_CFG.exists():
            try:
                data = json.loads(_AGENTS_CFG.read_text("utf-8"))
                for d in data.get("agents", []):
                    a = MainAgent.from_dict(d)
                    self._agents[a.id] = a
            except Exception:
                pass

    def _save(self) -> None:
        _AGENTS_CFG.parent.mkdir(parents=True, exist_ok=True)
        _AGENTS_CFG.write_text(
            json.dumps({"agents": [a.to_dict() for a in self._agents.values()]}, ensure_ascii=False, indent=2),
            "utf-8"
        )

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add(self, name: str, provider: str, model_id: str, api_key: str,
            role: str = "general", bio: str = "", is_leading: bool = False) -> MainAgent:
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        agent = MainAgent(
            id=agent_id, name=name, provider=provider, model_id=model_id,
            api_key=api_key, role=role, bio=bio, active=True, is_leading=is_leading,
        )
        self._agents[agent_id] = agent
        self._save()
        return agent

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False

    def get(self, agent_id: str) -> Optional[MainAgent]:
        return self._agents.get(agent_id)

    def get_by_name(self, name: str) -> Optional[MainAgent]:
        for a in self._agents.values():
            if a.name == name:
                return a
        return None

    def list_all(self) -> List[MainAgent]:
        return list(self._agents.values())

    def list_active(self) -> List[MainAgent]:
        return [a for a in self._agents.values() if a.active]

    def leading(self) -> Optional[MainAgent]:
        for a in self._agents.values():
            if a.is_leading and a.active:
                return a
        actives = self.list_active()
        return actives[0] if actives else None

    def set_active(self, agent_id: str, active: bool) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].active = active
            self._save()

    def set_leading(self, agent_id: str) -> None:
        for a in self._agents.values():
            a.is_leading = (a.id == agent_id)
        self._save()

    def update_ctx_pct(self, agent_id: str, pct: float) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].ctx_used_pct = pct
            self._save()

    def update_bio(self, agent_id: str, bio: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].bio = bio
            self._save()

    # ── Bio file ─────────────────────────────────────────────────────────────

    def load_bio_md(self, name: str) -> str:
        """Load agents/<name>.md if it exists."""
        path = _AGENTS_DIR / f"{name}.md"
        if path.exists():
            return path.read_text("utf-8")
        return ""

    def save_bio_md(self, name: str, content: str) -> None:
        _AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        (_AGENTS_DIR / f"{name}.md").write_text(content, "utf-8")

    # ── Family bios summary ──────────────────────────────────────────────────

    def family_summary(self, exclude_id: str | None = None) -> str:
        """Brief summary of all active agents for system prompt injection."""
        agents = [a for a in self.list_active() if a.id != exclude_id]
        if not agents:
            return ""
        lines = ["=== АКТИВНАЯ КОМАНДА ==="]
        for a in agents:
            lead_mark = " [ВЕДУЩИЙ]" if a.is_leading else ""
            ctx_pct = f" {a.ctx_used_pct:.0f}% ctx" if a.ctx_used_pct > 0 else ""
            lines.append(f"• {a.name} ({a.model_id}){lead_mark}{ctx_pct} — {a.role}")
            if a.bio:
                lines.append(f"  {a.bio[:120]}")
        return "\n".join(lines)


# Singleton
_crew_instance: Optional[Crew] = None


def get_crew() -> Crew:
    global _crew_instance
    if _crew_instance is None:
        _crew_instance = Crew()
    return _crew_instance

"""
favorite/agent/agent_registry.py — §7 AgentRegistry
Читает config/models_capabilities.json и предоставляет find_by_capability().
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional


_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_CAPS_FILE  = _CONFIG_DIR / "models_capabilities.json"


@dataclass
class AgentEntry:
    model_id:      str
    provider:      str
    capabilities:  List[str] = field(default_factory=list)
    vision:        bool = False
    image_gen:     bool = False
    audio_in:      bool = False
    audio_out:     bool = False
    web_search:    bool = False
    context_kb:    int  = 32
    cost_tier:     str  = "unknown"
    modalities_in: List[str] = field(default_factory=list)
    modalities_out: List[str] = field(default_factory=list)
    raw:           Dict = field(default_factory=dict)

    def has_capability(self, cap: str) -> bool:
        if cap in self.capabilities:
            return True
        # Boolean shorthand
        return bool(self.raw.get(cap, False))


class AgentRegistry:
    """Singleton registry of all known agent models with their capabilities."""

    _instance: Optional["AgentRegistry"] = None

    def __init__(self) -> None:
        self._agents: Dict[str, AgentEntry] = {}
        self._load()

    @classmethod
    def get(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reload(cls) -> "AgentRegistry":
        """Force reload from disk."""
        cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if not _CAPS_FILE.exists():
            return
        try:
            raw = json.loads(_CAPS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        for model_id, info in raw.items():
            self._agents[model_id] = AgentEntry(
                model_id=model_id,
                provider=info.get("provider", "unknown"),
                capabilities=info.get("capabilities", []),
                vision=bool(info.get("vision", False)),
                image_gen=bool(info.get("image_gen", False)),
                audio_in=bool(info.get("audio_in", False)),
                audio_out=bool(info.get("audio_out", False)),
                web_search=bool(info.get("web_search", False)),
                context_kb=int(info.get("context_kb", 32)),
                cost_tier=info.get("cost_tier", "unknown"),
                modalities_in=info.get("modalities_in", []),
                modalities_out=info.get("modalities_out", []),
                raw=info,
            )

    def all(self) -> List[AgentEntry]:
        return list(self._agents.values())

    def get_entry(self, model_id: str) -> Optional[AgentEntry]:
        return self._agents.get(model_id)

    def find_by_capability(self, cap: str) -> List[AgentEntry]:
        """Return all agents that have the given capability."""
        return [a for a in self._agents.values() if a.has_capability(cap)]

    def find_by_provider(self, provider: str) -> List[AgentEntry]:
        return [a for a in self._agents.values() if a.provider == provider]

    def find_free(self) -> List[AgentEntry]:
        return [a for a in self._agents.values() if a.cost_tier == "free"]

    def capabilities_matrix(self) -> str:
        """ASCII table: model × capability."""
        all_caps = set()
        for a in self._agents.values():
            all_caps.update(a.capabilities)
        all_caps_sorted = sorted(all_caps)
        col_w = max(len(c) for c in all_caps_sorted) if all_caps_sorted else 8
        header = "  {:<40}".format("Model") + "".join(f" {c:<{col_w}}" for c in all_caps_sorted)
        rows   = [header, "  " + "-" * len(header)]
        for model_id, a in self._agents.items():
            row = "  {:<40}".format(model_id[:40]) + "".join(
                " {:<{w}}".format("✓" if a.has_capability(c) else "·", w=col_w)
                for c in all_caps_sorted
            )
            rows.append(row)
        return "\n".join(rows)

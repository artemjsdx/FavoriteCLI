"""
favorite/skills/base.py — ISkill interface.
Every skill is a pair: <name>.py (code) + <name>.md (AI description).
"""
from abc import ABC, abstractmethod
from pathlib import Path


class ISkill(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Skill name (matches filename without extension)."""
        ...

    @property
    def enabled(self) -> bool:
        from .registry import SkillRegistry
        return SkillRegistry.is_enabled(self.name)

    @abstractmethod
    def run(self, args: str, ctx=None, cfg=None) -> str:
        """Execute the skill with given args string. Returns result string."""
        ...

    # Backwards-compat alias (some old code calls .execute())
    def execute(self, args: str) -> str:
        return self.run(args)

    def get_prompt_snippet(self) -> str:
        """Return a compact usage hint for the system prompt."""
        md_path = Path(__file__).parent / f"{self.name}.md"
        if md_path.exists():
            return md_path.read_text(encoding="utf-8")[:200]
        return f"Skill: {self.name}"

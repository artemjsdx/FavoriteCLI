"""
favorite/skills/websearch.py — Web search skill (ISkill wrapper).
"""
from .base import ISkill


class WebSearchSkill(ISkill):
    @property
    def name(self) -> str:
        return "websearch"

    def run(self, args: str, ctx=None, cfg=None) -> str:
        from ..skills.web_search import search as legacy_search
        try:
            return legacy_search(args)
        except Exception as e:
            return f"[websearch ERROR: {e}]"

# backwards compat alias
WebsearchSkill = WebSearchSkill

"""
favorite/skills/retry_skill.py
Retry skill — provides retry utilities for agent tasks.
"""
from ..skills.base import ISkill


class RetrySkill(ISkill):
    name = "retry"
    description = "Retry control skill — agent can request task retry with backoff."
    _prompt_snippet = (
        "Skill: retry — сигнализирует о необходимости повторной попытки.\n"
        "Usage: <RETRY:reason=причина>  (тег, не skill)"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        # The actual retry control is via <RETRY> tag in executor.py
        # This skill provides diagnostic info
        args = (args or "").strip()
        if args.startswith("status"):
            return "[retry: управление осуществляется через тег <RETRY:reason=...>]"
        return "[retry: используй тег <RETRY:reason=...> для запроса повтора]"

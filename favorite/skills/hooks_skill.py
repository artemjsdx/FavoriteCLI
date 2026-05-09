"""
favorite/skills/hooks_skill.py
Hooks system — run shell scripts on lifecycle events (on_message, on_done, on_push).
"""
import json
import subprocess
from pathlib import Path
from ..skills.base import ISkill

_HOOKS_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "hooks.json"

_DEFAULT_HOOKS = {
    "on_message": [],
    "on_done": [],
    "on_push": [],
    "on_error": [],
    "on_session_start": [],
    "on_session_end": [],
}


def _load_hooks() -> dict:
    if _HOOKS_CONFIG_FILE.exists():
        try:
            return json.loads(_HOOKS_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(_DEFAULT_HOOKS)


def fire_hooks(event: str, ctx=None, extra_env: dict | None = None) -> list[str]:
    """Fire all hooks for a given event. Returns list of outputs."""
    hooks = _load_hooks()
    commands = hooks.get(event, [])
    outputs = []
    if not commands:
        return outputs
    workdir = getattr(ctx, "workdir", ".") if ctx else "."
    for cmd in commands:
        try:
            env_override = {}
            if extra_env:
                import os
                env_override = {**os.environ, **extra_env}
            r = subprocess.run(
                cmd, shell=True, cwd=workdir, capture_output=True, text=True,
                timeout=15, env=env_override or None
            )
            out = (r.stdout or "").strip()
            err = (r.stderr or "").strip()
            combined = out + ("\n" + err if err else "")
            outputs.append(f"[hook:{event}] {cmd} → {combined[:200]}")
        except subprocess.TimeoutExpired:
            outputs.append(f"[hook:{event}] {cmd} → TIMEOUT")
        except Exception as e:
            outputs.append(f"[hook:{event}] {cmd} → ERROR: {e}")
    return outputs


class HooksSkill(ISkill):
    name = "hooks"
    description = "Manage lifecycle hooks — run shell scripts on events (on_done, on_push, etc.)."
    _prompt_snippet = (
        "Skill: hooks — выполняет shell-скрипты на события жизненного цикла агента.\n"
        "Events: on_message, on_done, on_push, on_error, on_session_start, on_session_end.\n"
        "Usage: <SKILL:name=hooks>list</SKILL> or <SKILL:name=hooks>fire:on_done</SKILL>"
    )

    def get_prompt_snippet(self) -> str:
        return self._prompt_snippet

    def run(self, args: str, ctx=None, cfg=None) -> str:
        args = (args or "").strip()
        if not args or args == "list":
            hooks = _load_hooks()
            lines = []
            for event, cmds in hooks.items():
                status = f"{len(cmds)} команд" if cmds else "нет"
                lines.append(f"  {event}: {status}")
            return "Hooks:\n" + "\n".join(lines)

        if args.startswith("fire:"):
            event = args[5:].strip()
            outputs = fire_hooks(event, ctx=ctx)
            return "\n".join(outputs) if outputs else f"[hooks: нет хуков для события {event}]"

        return f"[hooks: неизвестная команда '{args}'. Используй: list | fire:<event>]"

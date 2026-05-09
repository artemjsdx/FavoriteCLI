"""
favorite/skills/registry.py — auto-discovery and registration of skills.
"""
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import ISkill

_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "skills.json"

_DEFAULT_CONFIG = {
    "websearch":             {"enabled": True,  "lazy": False},
    "fetch_url":             {"enabled": True,  "lazy": False},
    "fs_tools":              {"enabled": True,  "lazy": False},
    "termux_shell":          {"enabled": True,  "lazy": False},
    "sleep":                 {"enabled": True,  "lazy": False},
    "notification_composer": {"enabled": False, "lazy": False},
    "tts_announce":          {"enabled": False, "lazy": False},
    "internet":              {"enabled": False, "lazy": True, "ready": False},
    "ocr":                   {"enabled": False, "lazy": True, "ready": False},
    "obsidian":              {"enabled": False, "lazy": False},
    "markitdown":            {"enabled": False, "lazy": True, "ready": False},
    "ocr_local":             {"enabled": False, "lazy": True, "ready": False},
}


class SkillRegistry:
    _skills: dict[str, "ISkill"] = {}
    _config: dict = {}

    @classmethod
    def load_config(cls) -> None:
        if _CONFIG_FILE.exists():
            try:
                cls._config = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                return
            except Exception:
                pass
        cls._config = dict(_DEFAULT_CONFIG)
        cls._save_config()

    @classmethod
    def _save_config(cls) -> None:
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(cls._config, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        if not cls._config:
            cls.load_config()
        entry = cls._config.get(name, {})
        if isinstance(entry, bool):
            return entry
        return entry.get("enabled", False)

    @classmethod
    def set_enabled(cls, name: str, enabled: bool) -> None:
        if not cls._config:
            cls.load_config()
        if name not in cls._config:
            cls._config[name] = {}
        if isinstance(cls._config[name], bool):
            cls._config[name] = {"enabled": enabled}
        else:
            cls._config[name]["enabled"] = enabled
        cls._save_config()

    @classmethod
    def register(cls, skill: "ISkill") -> None:
        cls._skills[skill.name] = skill

    @classmethod
    def get(cls, name: str) -> "ISkill | None":
        return cls._skills.get(name)

    @classmethod
    def all_skills(cls) -> list["ISkill"]:
        return list(cls._skills.values())

    @classmethod
    def enabled_skills(cls) -> list["ISkill"]:
        return [s for s in cls._skills.values() if s.enabled]

    @classmethod
    def autodiscover(cls) -> None:
        """Auto-discover and register all skills in the skills/ directory."""
        import importlib
        cls.load_config()
        skills_dir = Path(__file__).parent
        for py_file in sorted(skills_dir.glob("*.py")):
            if py_file.stem in ("base", "registry", "__init__", "web_search", "telegram_notify"):
                continue  # skip meta files and legacy names
            try:
                mod = importlib.import_module(f".{py_file.stem}", package="favorite.skills")
                # Look for ISkill subclasses
                from .base import ISkill
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    try:
                        if (isinstance(attr, type) and issubclass(attr, ISkill)
                                and attr is not ISkill):
                            instance = attr()
                            cls.register(instance)
                    except Exception:
                        pass
            except Exception:
                pass

    @classmethod
    def list_for_prompt(cls) -> str:
        """Generate the skills block for system prompt (lazy mode)."""
        enabled = cls.enabled_skills()
        if not enabled:
            return ""
        lines = [
            "=== Скиллы ===",
            f"Активных скиллов: {len(enabled)}.",
            "Вызов: <SKILL:name=<имя>>запрос</SKILL>",
            "Доступные: " + ", ".join(s.name for s in enabled),
        ]
        return "\n".join(lines)

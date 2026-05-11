"""
favorite/skills/__init__.py - registers all built-in skills at import time.
"""
from .registry import SkillRegistry

_BUILTINS = [
    ("websearch",      "favorite.skills.websearch",               "WebSearchSkill"),
    ("fetch_url",      "favorite.skills.fetch_url",               "FetchUrlSkill"),
    ("fs_tools",       "favorite.skills.fs_tools",                "FsToolsSkill"),
    ("compaction",     "favorite.skills.compaction_skill",        "CompactionSkill"),
    ("hooks",          "favorite.skills.hooks_skill",             "HooksSkill"),
    ("auto_context",   "favorite.skills.auto_context_skill",      "AutoContextSkill"),
    ("retry",          "favorite.skills.retry_skill",             "RetrySkill"),
    ("web_panel",      "favorite.skills.web_panel.panel",         "WebPanelSkill"),
    ("internet",       "favorite.skills.internet_skill",          "InternetSkill"),
    ("ocr",            "favorite.skills.ocr_skill",               "OcrSkill"),
    ("markitdown",     "favorite.skills.markitdown_skill",        "MarkitdownSkill"),
    ("obsidian",       "favorite.skills.obsidian_skill",          "ObsidianSkill"),
    ("tg_bot_input",   "favorite.skills.tg_bot_input_skill",      "TgBotInputSkill"),
    ("device_ctrl",    "favorite.skills.device_ctrl",             "DeviceCtrlSkill"),
]


def _register_builtins() -> None:
    for name, module_path, class_name in _BUILTINS:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            SkillRegistry.register(cls())
        except Exception as exc:
            import sys
            print(f"[skills] WARNING: could not load skill '{name}': {exc}", file=sys.stderr)


_register_builtins()

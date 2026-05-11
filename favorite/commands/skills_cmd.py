"""
favorite/commands/skills_cmd.py
Interactive skills panel — numbered toggle + per-skill settings submenu.
Supports clear-screen transitions and VoidAI key entry.
"""
import os
import sys
from .base import ICommand, CommandContext

# ── Skill registry ────────────────────────────────────────────────────────────
# Each entry: (skill_id, display_name, description, default_enabled, settings)
# settings: list of (key, label, type, options_or_default)
#   type "choice"  → options = [(value, description), ...]
#   type "text"    → options = default_display_label (str)
SKILLS = [
    ("WebSearch", "WebSearch", "Поиск в интернете", True, [
        ("provider", "Провайдер поиска", "choice", [
            ("auto",   "VoidAI → DDG (авто-фоллбек)"),
            ("voidai", "Только VoidAI / Sonar"),
            ("ddg",    "Только DuckDuckGo"),
        ]),
        ("voidai_key", "VoidAI API ключ", "text", "sk-va-unified-..."),
    ]),
    ("FetchURL", "Fetch URL", "Скачать и распарсить страницу", True, [
        ("timeout", "Таймаут (сек)", "choice", [
            ("10", "10 сек"),
            ("15", "15 сек"),
            ("20", "20 сек"),
            ("30", "30 сек"),
        ]),
    ]),
    ("FSTools",        "FS Tools",     "Чтение/запись файлов в workdir", True,  []),
    ("TermuxShell",    "Termux Shell", "Запуск команд в терминале",      True,  [
        ("timeout", "Таймаут команды (сек)", "choice", [
            ("15",  "15 сек"),
            ("30",  "30 сек"),
            ("60",  "60 сек"),
            ("120", "120 сек"),
        ]),
    ]),
    ("Sleep",          "Sleep",        "Отложенный запуск / ожидание",   True,  []),
    ("web_panel",      "web_panel",    "Веб-панель (FastAPI+WebSocket)",  False, []),
    ("device_ctrl",    "device_ctrl",  "Управление Android через ADB",   False, [
          ("_note", "Настройка ADB", "note", "Используй /device для настройки: IP, порт, Vision-модель"),
      ]),
]

_O  = "\033[38;2;255;140;0m"    # orange
_G  = "\033[38;2;80;200;100m"   # green
_R  = "\033[38;2;190;70;70m"    # red
_GR = "\033[38;2;110;110;110m"  # gray
_D  = "\033[2m"                  # dim
_B  = "\033[1m"                  # bold
_X  = "\033[0m"                  # reset

_W   = 40
_SEP = f"  {_GR}{'─' * _W}{_X}"


def _cls() -> None:
    """Clear terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _p(s: str = "") -> None:
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def _mask_key(key: str) -> str:
    """Show first 8 and last 4 chars of a key, mask middle."""
    if not key or key == "":
        return f"{_GR}не задан{_X}"
    if len(key) <= 14:
        return f"{_O}{'*' * len(key)}{_X}"
    return f"{_O}{key[:8]}{'*' * (len(key) - 12)}{key[-4:]}{_X}"


def _render(states: list[bool], cfg) -> None:
    _cls()
    active = sum(states)
    _p()
    _p(f"  {_B}{_O}⚡ Скиллы{_X}  {_GR}{active} из {len(SKILLS)} активно{_X}")
    _p(_SEP)
    _p()
    for i, (sid, disp, desc, default_on, settings) in enumerate(SKILLS, 1):
        on = states[i - 1]
        dot   = f"{_G}◆{_X}" if on else f"{_GR}○{_X}"
        state = f"{_G}ON {_X}" if on else f"{_R}OFF{_X}"
        hint  = f" {_GR}[s{i}]{_X}" if settings else ""
        pad   = " " * max(0, 13 - len(disp))
        _p(f"  {_GR}{i}{_X}  {dot}  {_B}{disp}{_X}{pad}  {state}{hint}")
        _p(f"       {_GR}{desc[:36]}{_X}")
        if settings and on:
            for setting in settings:
                key, label, stype = setting[0], setting[1], setting[2]
                opts_or_def = setting[3]
                if stype == "choice":
                    cur = cfg.skill_setting(sid, key, opts_or_def[0][0])
                    _p(f"       {_GR}└─ {label}: {_O}{cur}{_X}")
                elif stype == "text":
                    # VoidAI key — read from cfg.void_ai_key
                    if key == "voidai_key":
                        cur = cfg.void_ai_key or ""
                    else:
                        cur = cfg.skill_setting(sid, key, "")
                    _p(f"       {_GR}└─ {label}: {_mask_key(cur)}{_X}")
        _p()
    _p(_SEP)
    _p(f"  {_GR}[1-{len(SKILLS)}]{_X} вкл/выкл  {_GR}[s1..]{_X} настройки  {_GR}[q]{_X} выход")
    _p(_SEP)
    _p()


def _cur_val(sid, key, stype, opts_or_def, cfg):
    if stype == "text":
        v = (cfg.void_ai_key or "") if key == "voidai_key" else cfg.skill_setting(sid, key, "")
        return _mask_key(v)
    cur = cfg.skill_setting(sid, key, opts_or_def[0][0])
    return f"{_O}{cur}{_X}"


def _edit_choice(sid, disp, key, label, options, cfg):
    while True:
        cur = cfg.skill_setting(sid, key, options[0][0])
        _cls()
        _p()
        _p(f"  {_B}{_O}{disp}{_X}  {_GR}›  {label}{_X}")
        _p(_SEP)
        for j, (val, val_desc) in enumerate(options, 1):
            active   = val == cur
            marker   = f"{_O}◆{_X}" if active else f"{_GR}○{_X}"
            cur_lbl  = f"  {_G}← сейчас{_X}" if active else ""
            name_fmt = f"{_B}{val}{_X}" if active else f"{_GR}{val}{_X}"
            pad = " " * max(0, 8 - len(val))
            _p(f"  {_GR}{j}{_X}  {marker}  {name_fmt}{pad}  {_GR}{val_desc}{_X}{cur_lbl}")
        _p()
        _p(_SEP)
        _p(f"  {_GR}Введи номер или Enter → назад{_X}")
        _p()
        try:
            raw = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw.isdigit():
            j = int(raw)
            if 1 <= j <= len(options):
                cfg.set_skill_setting(sid, key, options[j - 1][0])
            break


def _edit_text(sid, disp, key, label, cfg):
    while True:
        _cls()
        _p()
        _p(f"  {_B}{_O}{disp}{_X}  {_GR}›  {label}{_X}")
        _p(_SEP)
        _p()
        cur = (cfg.void_ai_key or "") if key == "voidai_key" else cfg.skill_setting(sid, key, "")
        _p(f"  Текущее: {_mask_key(cur)}")
        _p()
        _p(f"  {_GR}Введи значение (Enter → назад, 'clear' → удалить):{_X}")
        _p()
        _p(_SEP)
        _p()
        try:
            raw = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw.lower() == "clear":
            if key == "voidai_key":
                cfg.set_void_ai_key("")
            else:
                cfg.set_skill_setting(sid, key, "")
            _p(f"  {_G}✓{_X} Очищено")
            break
        if key == "voidai_key":
            cfg.set_void_ai_key(raw)
        else:
            cfg.set_skill_setting(sid, key, raw)
        _p(f"  {_G}✓{_X} Сохранено")
        break


def _settings_menu(idx: int, cfg) -> None:
    sid, disp, desc, default_on, settings = SKILLS[idx]
    if not settings:
        _cls()
        _p()
        _p(f"  {_GR}У скилла {_B}{disp}{_X}{_GR} нет настроек.{_X}")
        _p()
        try:
            input("  → ")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    # Если все настройки — только note (информационные), показываем и выходим
    if all(len(s) >= 3 and s[2] == "note" for s in settings):
        _cls()
        _p()
        _p(f"  {_B}{_O}{disp}{_X}  {_GR}›  настройки{_X}")
        _p(_SEP)
        _p()
        for s in settings:
            _p(f"  {_O}ℹ  {s[1]}:{_X}")
            _p(f"     {_GR}{s[3]}{_X}")
            _p()
        _p(_SEP)
        _p(f"  {_GR}Enter → назад{_X}")
        _p()
        try:
            input("  → ")
        except (EOFError, KeyboardInterrupt):
            pass
        return
    while True:
        _cls()
        _p()
        _p(f"  {_B}{_O}{disp}{_X}  {_GR}›  настройки{_X}")
        _p(_SEP)
        _p()
        for j, setting in enumerate(settings, 1):
            key, label, stype, opts_or_def = setting
            val = _cur_val(sid, key, stype, opts_or_def, cfg)
            _p(f"  {_GR}{j}{_X}  {_B}{label}{_X}  {_GR}:{_X} {val}")
            _p()
        _p(_SEP)
        _p(f"  {_GR}Введи номер или Enter → назад{_X}")
        _p()
        try:
            raw = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw.isdigit():
            j = int(raw) - 1
            if 0 <= j < len(settings):
                key, label, stype, opts_or_def = settings[j]
                if stype == "choice":
                    _edit_choice(sid, disp, key, label, opts_or_def, cfg)
                else:
                    _edit_text(sid, disp, key, label, cfg)

class SkillsCommand(ICommand):
    name = "/skills"
    description = "Управление скиллами"
    priority = 8

    def execute(self, args: str, ctx: CommandContext) -> None:
        from ..config.loader import get_config
        cfg = get_config()
        parts = args.strip().split()
        if len(parts) == 2 and parts[1].lower() in ("on", "off"):
            sid = parts[0]
            enabled = parts[1].lower() == "on"
            cfg.set_skill_enabled(sid, enabled)
            state = f"{_G}ON{_X}" if enabled else f"{_R}OFF{_X}"
            _p(f"\n  {state}  {_B}{sid}{_X}\n")
            return
        while True:
            states = [cfg.skill_enabled(sid, default_on) for sid, _, _, default_on, _ in SKILLS]
            _render(states, cfg)
            try:
                raw = input("  → ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if raw in ("q", "quit", "exit", ""):
                break
            if raw.startswith("s") and raw[1:].isdigit():
                idx = int(raw[1:]) - 1
                if 0 <= idx < len(SKILLS):
                    _settings_menu(idx, cfg)
                continue
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(SKILLS):
                    sid = SKILLS[idx][0]
                    new_state = not cfg.skill_enabled(sid, SKILLS[idx][3])
                    cfg.set_skill_enabled(sid, new_state)
                    # Sync runtime SkillRegistry (оно читает свой путь в skills.json)
                    try:
                        from favorite.skills.registry import SkillRegistry
                        SkillRegistry.set_enabled(sid, new_state)
                    except Exception:
                        pass
                continue

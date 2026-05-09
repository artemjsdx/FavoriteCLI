"""
favorite/commands/modules_cmd.py — §18.13 /modules command.
Full interactive module toggle screen matching the ТЗ spec.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_MODULES_FILE = _CONFIG_DIR / "modules.json"

# ── Module catalogue ────────────────────────────────────────────────────────
# Each entry: (key, display_name, section, type, default, description)
# type: "bool" | "choice" | "int"
_CATALOGUE: list[tuple] = [
    # §4 Execution
    ("action_bias_mode",                "Action bias mode",              "§4 Execution",      "choice", "balanced",   "balanced|bold|cautious"),
    ("verifier_mode",                   "Verifier mode",                 "§4 Execution",      "choice", "tag",        "tag|llm|off"),
    ("context_compaction_mode",         "Context compaction",            "§4 Execution",      "choice", "auto",       "auto|manual|off"),
    ("skill_context_mode",              "Skill context mode",            "§4 Execution",      "choice", "lazy",       "lazy|eager|off"),
    ("shell_output_limit",              "Shell output limit",            "§4 Execution",      "choice", "fixed",      "fixed|adaptive|off"),
    ("agent_mode",                      "Agent mode",                    "§4 Execution",      "choice", "pro",        "pro|lite|auto"),
    # §18.13 Cognitive
    ("reincarnation",                   "Реинкарнация",                  "§18 Cognitive",     "bool",   True,         "Перезапуск агента при переполнении контекста"),
    ("reincarnation_threshold_pct",     "  ↳ Порог, %",                 "§18 Cognitive",     "int",    90,           "При каком % контекста запускать (1-100)"),
    ("force_reincarnate_at_95",         "  ↳ Форсировать при 95%",      "§18 Cognitive",     "bool",   True,         "Принудительная реинкарнация при 95%"),
    ("reincarnation_keeper_selection",  "  ↳ Выбор хранителя",         "§18 Cognitive",     "choice", "auto",       "auto|agent_chooses|fixed"),
    ("cycle_detection",                 "Детектор циклов",               "§18 Cognitive",     "bool",   True,         "Обнаруживать и прерывать зацикливание"),
    ("cycle_similarity_threshold_pct",  "  ↳ Порог схожести, %",       "§18 Cognitive",     "int",    85,           "Порог схожести ответов для детектора (1-100)"),
    ("mandatory_snapshot_on_destructive","Снэпшот перед опасным",       "§18 Cognitive",     "bool",   True,         "Авто-снэпшот перед деструктивными операциями"),
    ("time_injection",                  "Инжекция времени",              "§18 Cognitive",     "bool",   True,         "Вставлять текущее время МСК в системный промпт"),
    ("family_bios_in_context",          "Биографии команды",             "§18 Cognitive",     "bool",   True,         "Включать биографии мейнов в системный промпт"),
    ("panic_prevention",                "Анти-паника",                   "§18 Cognitive",     "bool",   True,         "Блокировать панические ответы агента"),
    ("peer_request_expiry",             "Таймаут запросов к пирам",     "§18 Cognitive",     "bool",   True,         "Истекать запросы ASK_PEER/DELEGATE_PEER"),
    ("peer_request_expiry_sec",         "  ↳ Таймаут, сек",            "§18 Cognitive",     "int",    120,          "Время ожидания ответа от пира (секунды)"),
    ("wake_lock_on_auto",               "Wake lock в авто-режиме",       "§18 Cognitive",     "bool",   False,        "Блокировать засыпание экрана при /auto"),
    ("peer_voting",                     "Голосование пиров",             "§18 Cognitive",     "bool",   True,         "Разрешить VOTE теги и мажоритарное голосование"),
    ("peer_expertise_priority",         "Приоритет экспертизы",          "§18 Cognitive",     "bool",   True,         "Маршрутизировать задачи к компетентному пиру"),
    ("auto_rollback_on_validation_fail","Авто-откат при ошибке",         "§18 Cognitive",     "bool",   False,        "Откатить изменения если VERIFY провалился"),
    # §19.2 Auto parallelism
    ("auto_parallelism_mode",           "Режим параллелизма /auto",      "§19 Multi-Main",    "choice", "hybrid",     "unified|independent|hybrid"),
    ("peer_file_locks",                 "Блокировки файлов пиров",       "§19 Multi-Main",    "bool",   True,         "Предотвращать конфликты записи в общие файлы"),
    # §19.4 Telegram
    ("tg_routing_mode",                 "TG маршрутизация",              "§19 Telegram",      "choice", "leader_only","leader_only|per_agent_channels|family_topic_groups"),
    ("tg_digest",                       "TG дайджест",                   "§19 Telegram",      "bool",   False,        "Периодически отправлять дайджест в Telegram"),
    ("tg_digest_interval_sec",          "  ↳ Интервал, сек",           "§19 Telegram",      "int",    3600,         "Как часто отправлять дайджест"),
    ("tg_send_confirmations",           "TG подтверждения",              "§19 Telegram",      "bool",   True,         "Уведомлять в TG о REQUEST_CONFIRM"),
    ("tg_send_peer_disputes",           "TG споры пиров",                "§19 Telegram",      "bool",   True,         "Уведомлять в TG о разногласиях VOTE"),
    ("tg_send_task_events",             "TG события задач",              "§19 Telegram",      "bool",   True,         "ADD_TASK/COMPLETE_TASK → Telegram"),
    ("tg_send_reincarnations",          "TG реинкарнации",               "§19 Telegram",      "bool",   True,         "Уведомлять в TG о реинкарнациях"),
    # §19.6 Sub sandbox
    ("sub_sandbox",                     "Суб-сандбокс",                  "§19 Sub Sandbox",   "bool",   False,        "Субы работают в изолированном рабочем пространстве"),
    ("sub_change_review",               "Ревью изменений суба",          "§19 Sub Sandbox",   "bool",   True,         "Мейн проверяет каждое изменение суба перед применением"),
]


def _load() -> dict:
    if _MODULES_FILE.exists():
        try:
            return json.loads(_MODULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    _MODULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MODULES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _val_str(data: dict, key: str, default: Any) -> str:
    v = data.get(key, default)
    if isinstance(v, bool):
        return "[green]ON[/green]" if v else "[dim]OFF[/dim]"
    return f"[cyan]{v}[/cyan]"


def _show_modules(data: dict) -> None:
    console.print()
    console.print(Panel(
        Text("⚙  МОДУЛИ", style="bold #ff8c00"),
        subtitle="[dim]Введи номер для переключения | q — выход | ? — справка[/dim]",
        border_style="#ff8c00",
    ))

    table = Table(show_header=True, header_style="bold #ff8c00", box=None, padding=(0, 1))
    table.add_column("#",     style="dim", width=4)
    table.add_column("Модуль",             width=34)
    table.add_column("Значение",           width=18)
    table.add_column("Секция",             style="dim", width=18)

    for i, (key, name, section, typ, default, desc) in enumerate(_CATALOGUE, 1):
        val_str = _val_str(data, key, default)
        table.add_row(str(i), escape(name), val_str, escape(section))

    console.print(table)
    console.print()


def cmd_modules(args: list[str], ctx, cfg) -> None:
    """
    /modules

    Interactive module toggle screen.
    Enter number to toggle/change, 'q' to quit, '?' for help.
    """
    data = _load()

    # Fill in defaults for anything missing
    for key, name, section, typ, default, desc in _CATALOGUE:
        if key not in data:
            data[key] = default

    if args and args[0].lstrip("-").isdigit():
        # Direct toggle: /modules 7
        _toggle_by_index(data, int(args[0].lstrip("-")))
        _save(data)
        return

    while True:
        _show_modules(data)
        try:
            raw = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if raw.lower() in ("q", "quit", "exit", ""):
            break

        if raw == "?":
            _show_help()
            continue

        if raw.isdigit():
            idx = int(raw)
            changed = _toggle_by_index(data, idx)
            if changed:
                _save(data)
                key, name, *_ = _CATALOGUE[idx - 1]
                new_val = data.get(key)
                console.print(f"  [dim #888888]✓ {name} = {new_val}[/dim #888888]")
            continue

        # key=value assignment
        if "=" in raw:
            k, _, v = raw.partition("=")
            k = k.strip()
            v = v.strip()
            matched = next((c for c in _CATALOGUE if c[0] == k), None)
            if matched:
                key, name, section, typ, default, desc = matched
                data[key] = _coerce(v, typ)
                _save(data)
                console.print(f"  [dim #888888]✓ {name} = {data[key]}[/dim #888888]")
            else:
                console.print(f"  [red]Неизвестный ключ:[/red] {k}")
            continue

        console.print(f"  [dim]Введи номер (1-{len(_CATALOGUE)}), key=value, или q[/dim]")


def _toggle_by_index(data: dict, idx: int) -> bool:
    if not (1 <= idx <= len(_CATALOGUE)):
        console.print(f"  [red]Нет модуля #{idx}[/red]")
        return False
    key, name, section, typ, default, desc = _CATALOGUE[idx - 1]
    current = data.get(key, default)
    if typ == "bool":
        data[key] = not bool(current)
    elif typ == "choice":
        choices = desc.split("|")
        try:
            cur_idx = choices.index(str(current))
        except ValueError:
            cur_idx = 0
        data[key] = choices[(cur_idx + 1) % len(choices)]
    elif typ == "int":
        console.print(f"  [dim]Текущее: {current}. Введи новое значение:[/dim]")
        try:
            new_v = input("  → ").strip()
            data[key] = int(new_v)
        except (ValueError, EOFError):
            return False
    return True


def _coerce(v: str, typ: str) -> Any:
    if typ == "bool":
        return v.lower() in ("true", "1", "on", "yes", "да")
    if typ == "int":
        try:
            return int(v)
        except ValueError:
            return v
    return v


def _show_help() -> None:
    console.print()
    console.print("[bold]Справка /modules:[/bold]")
    console.print("  [cyan]7[/cyan]          — переключить модуль #7")
    console.print("  [cyan]key=value[/cyan]  — установить конкретное значение")
    console.print("  [cyan]q[/cyan]          — выйти")
    console.print()
    console.print("[bold]Типы значений:[/bold]")
    console.print("  [green]bool[/green]   — ON/OFF переключатель")
    console.print("  [cyan]choice[/cyan] — выбор из вариантов (переключается по кругу)")
    console.print("  [yellow]int[/yellow]    — числовое значение")
    console.print()


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class ModulesCommand(ICommand):
    name = "/modules"
    description = "Модули агента — переключение настроек"
    priority = 60

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_modules(arg_list, ctx, getattr(ctx, "config", None))

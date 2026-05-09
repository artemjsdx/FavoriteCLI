"""
favorite/commands/prompt_audit_cmd.py — hidden /prompt-audit command.
Shows token counts for all system prompt parts and flags overruns.
"""
from __future__ import annotations

from pathlib import Path
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

console = Console()
_BASE = Path(__file__).resolve().parent.parent.parent


def _count_tokens_approx(text: str) -> int:
    """Approximate token count: chars / 4 (fast, no tiktoken required)."""
    return len(text) // 4


def _count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return _count_tokens_approx(text)


def cmd_prompt_audit(args: list[str], ctx, cfg) -> None:
    """
    /prompt-audit

    Audits all system prompt components:
    - Counts tokens per section
    - Highlights sections exceeding budget
    - Shows total vs model context limit
    """
    parts: list[tuple[str, str]] = []

    # 1. Try to get the live system prompt
    try:
        from ..agent.system_prompt import build_system_prompt
        full = build_system_prompt(cfg=cfg, workdir=ctx.workdir, session_id=ctx.session_id)
        parts.append(("FULL system prompt", full))
    except Exception as e:
        parts.append(("FULL system prompt", f"[ERROR loading: {e}]"))

    # 2. Prompts directory .md files
    prompts_dir = _BASE / "favorite" / "prompts"
    if prompts_dir.exists():
        for md in sorted(prompts_dir.rglob("*.md")):
            try:
                text = md.read_text(encoding="utf-8")
                parts.append((str(md.relative_to(_BASE)), text))
            except Exception as e:
                parts.append((str(md.relative_to(_BASE)), f"[ERROR: {e}]"))

    # 3. sub_roles_library.json
    roles_file = _BASE / "favorite" / "agent" / "sub_roles_library.json"
    if roles_file.exists():
        try:
            import json
            roles = json.loads(roles_file.read_text(encoding="utf-8"))
            text  = " ".join(r.get("description", "") + " " + r.get("name", "") for r in roles)
            parts.append(("sub_roles_library.json", text))
        except Exception:
            pass

    BUDGET_WARN  = 1200   # tokens per section
    BUDGET_ERROR = 2000

    table = Table(show_header=True, header_style="bold #ff8c00", box=None, padding=(0, 1))
    table.add_column("Секция",        width=40)
    table.add_column("Токенов",       width=10, justify="right")
    table.add_column("Символов",      width=10, justify="right")
    table.add_column("Статус",        width=12)

    total_tokens = 0
    for name, text in parts:
        toks = _count_tokens(text)
        chars = len(text)
        total_tokens += toks
        if toks >= BUDGET_ERROR:
            status = "[bold red]OVERSHOOT[/bold red]"
        elif toks >= BUDGET_WARN:
            status = "[yellow]warn[/yellow]"
        else:
            status = "[dim]ok[/dim]"
        table.add_row(escape(name[:40]), str(toks), str(chars), status)

    console.print()
    console.print(Panel(
        table,
        title="[bold #ff8c00]🔍 /prompt-audit[/bold #ff8c00]",
        subtitle=f"[dim]Итого ~{total_tokens} токенов | tiktoken {'доступен' if _has_tiktoken() else 'нет (≈÷4)'}[/dim]",
        border_style="#ff8c00",
    ))


def _has_tiktoken() -> bool:
    try:
        import tiktoken  # noqa
        return True
    except ImportError:
        return False


# ── ICommand wrapper (backward-compat with app.py registry) ──────────────────
from .base import ICommand, CommandContext as _CC

class PromptAuditCommand(ICommand):
    name = "/prompt-audit"
    description = "Аудит системного промпта — токены по секциям [скрытая]"
    priority = 99

    def execute(self, args: str, ctx: _CC) -> None:
        arg_list = args.split() if args.strip() else []
        cmd_prompt_audit(arg_list, ctx, getattr(ctx, "config", None))

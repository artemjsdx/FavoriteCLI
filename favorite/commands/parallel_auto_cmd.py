"""
favorite/commands/parallel_auto_cmd.py — Parallel /auto (§19.2).

Modes:
  unified     — all agents work on the SAME task, results merged/voted
  independent — each agent gets its OWN task slice, runs in parallel threads
  hybrid      — coordinator (main-1) splits task → assigns slices → aggregates

Usage:
  /parallel unified <task>
  /parallel independent <task>
  /parallel hybrid <task>
"""
import threading
from typing import Optional
from rich.console import Console
from rich.markup import escape
from rich.text import Text
from .base import ICommand, CommandContext

console = Console()
_SEP = "[dim #2a2a2a]" + "─" * 50 + "[/dim #2a2a2a]"


class ParallelAutoCommand(ICommand):
    name = "/parallel"
    description = "Параллельный /auto: unified | independent | hybrid (§19.2)"
    priority = 5

    def execute(self, args: str, ctx: CommandContext) -> None:
        parts = args.strip().split(None, 1)
        mode  = parts[0].lower() if parts else ""
        task  = parts[1].strip() if len(parts) > 1 else ""

        if mode not in ("unified", "independent", "hybrid"):
            self._show_help()
            return
        if not task:
            console.print("  [red]Укажи задачу после режима.[/red]")
            return

        agents = _load_active_agents(ctx)
        if not agents:
            console.print("  [dim]Нет активных агентов. Создай через [bold]/agents[/bold].[/dim]")
            return

        console.print()
        console.print(f"  [bold #ff8c00]◈ PARALLEL AUTO[/bold #ff8c00]  "
                      f"[dim]режим:[/dim] [white]{mode}[/white]  "
                      f"[dim]агентов:[/dim] [cyan]{len(agents)}[/cyan]")
        console.print(f"  [dim #555555]{escape(task[:80])}[/dim #555555]")
        console.print()

        if mode == "unified":
            _run_unified(task, agents, ctx)
        elif mode == "independent":
            _run_independent(task, agents, ctx)
        elif mode == "hybrid":
            _run_hybrid(task, agents, ctx)

    def _show_help(self) -> None:
        console.print()
        console.print("  [bold white]Параллельный /auto (§19.2)[/bold white]")
        console.print()
        console.print("  [dim #666666]unified[/dim #666666]     — все агенты решают одну задачу, результат голосованием")
        console.print("  [dim #666666]independent[/dim #666666] — каждый агент получает свой кусок задачи")
        console.print("  [dim #666666]hybrid[/dim #666666]      — координатор разбивает на части и раздаёт")
        console.print()
        console.print("  Пример: [bold]/parallel unified разработай модуль auth.py[/bold]")
        console.print()


# ── Mode: unified ─────────────────────────────────────────────────────────────

def _run_unified(task: str, agents: list[dict], ctx: CommandContext) -> None:
    """All agents solve the same task; winning answer chosen by vote."""
    from ..agent.sub_agent import run_sub_agent
    from ..ui.chat import print_status_line, print_agent_message
    cfg = ctx.config

    results: dict[str, str] = {}
    lock = threading.Lock()

    def _worker(agent: dict) -> None:
        aid   = agent["id"]
        role  = agent.get("role_id", "analyst")
        model = agent.get("model")
        key   = agent.get("api_key")
        prov  = agent.get("provider")
        try:
            res = run_sub_agent(role, task, cfg, model=model, api_key=key, provider=prov, ctx=ctx)
            with lock:
                results[aid] = res.strip()
        except Exception as e:
            with lock:
                results[aid] = f"[error: {e}]"

    threads = [threading.Thread(target=_worker, args=(a,), daemon=True) for a in agents]
    for t in threads: t.start()
    for t in threads: t.join(timeout=90)

    # Display all results
    console.print()
    for aid, res in results.items():
        console.print(f"  [bold cyan]{aid}[/bold cyan]")
        console.print(f"  [dim #888888]{escape(res[:300])}[/dim #888888]")
        console.print()

    # If multiple results: vote on best answer
    if len(results) > 1:
        try:
            from ..agent.vote import run_vote
            options = [f"{aid}: {r[:60]}" for aid, r in results.items()]
            vote_result = run_vote(
                question=f"Лучший ответ на задачу: {task[:60]}",
                options=list(results.keys()),
                session_id=ctx.session_id,
                workdir=ctx.workdir,
                cfg=cfg, ctx=ctx,
                timeout=5,
            )
            winner_id = vote_result.get("winner", list(results.keys())[0])
            console.print(f"  [bold #5fd7af]● UNIFIED WINNER:[/bold #5fd7af] [cyan]{winner_id}[/cyan]")
            print_agent_message(results.get(winner_id, ""))
        except Exception:
            # No vote — just show all
            pass
    elif results:
        print_agent_message(list(results.values())[0])


# ── Mode: independent ─────────────────────────────────────────────────────────

def _run_independent(task: str, agents: list[dict], ctx: CommandContext) -> None:
    """
    Split task into N parts (one per agent), run all in parallel, aggregate.
    Task splitting uses LLM or simple line/word chunking.
    """
    from ..agent.sub_agent import run_sub_agent
    from ..agent.llm import call_llm
    from ..ui.chat import print_agent_message
    cfg = ctx.config

    # Ask coordinator to split task
    slices = _split_task(task, len(agents), cfg)
    results: dict[str, str] = {}
    lock = threading.Lock()

    console.print(f"  [dim]Разбил на {len(slices)} части:[/dim]")
    for i, s in enumerate(slices):
        console.print(f"  [dim #666666]{i+1}.[/dim #666666] {escape(s[:80])}")
    console.print()

    def _worker(agent: dict, slice_task: str) -> None:
        aid  = agent["id"]
        role = agent.get("role_id", "analyst")
        model = agent.get("model"); key = agent.get("api_key"); prov = agent.get("provider")
        try:
            res = run_sub_agent(role, slice_task, cfg, model=model, api_key=key, provider=prov, ctx=ctx)
            with lock: results[aid] = res.strip()
        except Exception as e:
            with lock: results[aid] = f"[error: {e}]"

    pairs = list(zip(agents, slices))
    threads = [threading.Thread(target=_worker, args=(a, s), daemon=True) for a, s in pairs]
    for t in threads: t.start()
    for t in threads: t.join(timeout=90)

    # Aggregate
    combined = "\n\n".join(f"## [{aid}]\n{res}" for aid, res in results.items())
    console.print()
    console.print("  [bold #ff8c00]◈ INDEPENDENT — Агрегированный результат:[/bold #ff8c00]")
    print_agent_message(combined)


# ── Mode: hybrid ──────────────────────────────────────────────────────────────

def _run_hybrid(task: str, agents: list[dict], ctx: CommandContext) -> None:
    """
    Main agent (coordinator) plans subtasks → delegates to workers → aggregates.
    """
    from ..agent.sub_agent import run_sub_agent
    from ..agent.llm import call_llm
    from ..ui.chat import print_agent_message
    cfg = ctx.config

    console.print("  [dim]Координатор планирует подзадачи…[/dim]")

    # Step 1: coordinator generates plan
    plan_prompt = (
        f"You are a coordinator. Split this task into {len(agents)} subtasks.\n"
        f"Return ONLY a numbered list, one subtask per line.\n\n"
        f"Task: {task}"
    )
    try:
        plan_raw = call_llm(
            [{"role": "system", "content": "You are a task coordinator."},
             {"role": "user",   "content": plan_prompt}],
            cfg,
        )
        subtasks = [l.strip().lstrip("0123456789.-) ") for l in plan_raw.splitlines() if l.strip()][:len(agents)]
    except Exception:
        subtasks = [task] * len(agents)

    console.print(f"  [dim]Подзадачи ({len(subtasks)}):[/dim]")
    for i, s in enumerate(subtasks):
        console.print(f"  [dim #666666]{i+1}.[/dim #666666] {escape(s[:80])}")
    console.print()

    # Step 2: run workers
    results: dict[str, str] = {}
    lock = threading.Lock()

    def _worker(agent: dict, subtask: str) -> None:
        aid  = agent["id"]
        role = agent.get("role_id", "analyst")
        model = agent.get("model"); key = agent.get("api_key"); prov = agent.get("provider")
        try:
            res = run_sub_agent(role, subtask, cfg, model=model, api_key=key, provider=prov, ctx=ctx)
            with lock: results[aid] = res.strip()
        except Exception as e:
            with lock: results[aid] = f"[error: {e}]"

    pairs = list(zip(agents, subtasks))
    threads = [threading.Thread(target=_worker, args=(a, s), daemon=True) for a, s in pairs]
    for t in threads: t.start()
    for t in threads: t.join(timeout=90)

    # Step 3: coordinator aggregates
    console.print("  [dim]Координатор агрегирует результаты…[/dim]")
    parts_text = "\n\n".join(f"[{aid}] {r}" for aid, r in results.items())
    agg_prompt = (
        f"Original task: {task}\n\n"
        f"Worker results:\n{parts_text[:6000]}\n\n"
        f"Synthesize a final cohesive answer. Be concise."
    )
    try:
        final = call_llm(
            [{"role": "system", "content": "You synthesize multi-agent results."},
             {"role": "user",   "content": agg_prompt}],
            cfg,
        )
    except Exception as e:
        final = f"[aggregation error: {e}]\n\n" + parts_text

    console.print()
    console.print("  [bold #ff8c00]◈ HYBRID — Финальный результат:[/bold #ff8c00]")
    print_agent_message(final)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_active_agents(ctx: CommandContext) -> list[dict]:
    import json
    from pathlib import Path
    ua_file = Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"
    if not ua_file.exists():
        return []
    try:
        data = json.loads(ua_file.read_text(encoding="utf-8"))
        return [a for a in data.get("agents", []) if a.get("active", True)]
    except Exception:
        return []


def _split_task(task: str, n: int, cfg) -> list[str]:
    """Split task into n parts. LLM-based, falls back to word chunks."""
    if n <= 1:
        return [task]
    try:
        from ..agent.llm import call_llm
        prompt = (
            f"Split this task into exactly {n} independent subtasks.\n"
            f"Return ONLY a numbered list.\n\nTask: {task}"
        )
        raw = call_llm(
            [{"role": "system", "content": "Split tasks into subtasks."},
             {"role": "user",   "content": prompt}],
            cfg,
        )
        parts = [l.strip().lstrip("0123456789.-) ") for l in raw.splitlines() if l.strip()]
        if len(parts) >= n:
            return parts[:n]
    except Exception:
        pass
    # Fallback: duplicate task for each agent
    return [task] * n

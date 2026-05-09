"""
favorite/agent/vote.py — VOTE polling system (§16.9).

Agents emit <VOTE:question="...">option1|option2|option3</VOTE>
The system writes the vote to disk, spawns peer sub-agents to cast ballots,
aggregates results, and returns the winning option.

Tag syntax:
  <VOTE:question="Deploy now?" timeout="30">yes|no|later</VOTE>
  <VOTE:question="Pick approach?" agents="agent-1,agent-2">fast|safe|hybrid</VOTE>
"""
import json
import time
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


_VOTE_DIR_NAME = "votes"        # relative to sessions/<id>/
_DEFAULT_TIMEOUT = 20           # seconds to wait for peer votes
_DEFAULT_AGENTS  = 3            # max peer agents to ask


# ── Public API ────────────────────────────────────────────────────────────────

def run_vote(
    question: str,
    options: list[str],
    session_id: str,
    workdir: str,
    cfg=None,
    ctx=None,
    timeout: int = _DEFAULT_TIMEOUT,
    agent_ids: list[str] | None = None,
) -> dict:
    """
    Full vote lifecycle:
      1. Write vote manifest to disk
      2. Spawn peer sub-agents to cast ballots (non-blocking threads)
      3. Wait up to *timeout* seconds for all votes
      4. Tally and return result dict

    Returns:
        {
            "vote_id": str,
            "question": str,
            "options": list[str],
            "votes": {option: count},
            "winner": str,
            "total": int,
            "unanimous": bool,
        }
    """
    if len(options) < 2:
        return _trivial_result(question, options)

    vote_id   = str(uuid.uuid4())[:8]
    vote_dir  = _vote_dir(workdir, session_id)
    vote_dir.mkdir(parents=True, exist_ok=True)
    manifest  = vote_dir / f"{vote_id}.json"

    # Write manifest — peers will write their ballot file alongside it
    manifest.write_text(json.dumps({
        "vote_id":    vote_id,
        "question":   question,
        "options":    options,
        "created_at": datetime.utcnow().isoformat(),
        "status":     "open",
        "ballots":    {},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    _show_vote_banner(question, options, vote_id)

    # Spawn peer sub-agents in background threads
    targets = _resolve_agents(agent_ids, cfg)[:_DEFAULT_AGENTS]
    threads = []
    for agent_id in targets:
        t = threading.Thread(
            target=_peer_vote,
            args=(vote_id, question, options, agent_id, manifest, cfg, ctx),
            daemon=True,
        )
        t.start()
        threads.append(t)

    # Wait for all threads up to timeout
    deadline = time.monotonic() + timeout
    for t in threads:
        remaining = max(0.1, deadline - time.monotonic())
        t.join(timeout=remaining)

    # Read ballots from manifest
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        ballots = data.get("ballots", {})
    except Exception:
        ballots = {}

    return _tally(vote_id, question, options, ballots, manifest)


def cast_ballot(vote_id: str, agent_id: str, choice: str,
                workdir: str, session_id: str) -> bool:
    """External API: an agent writes its ballot. Safe to call from any thread."""
    try:
        manifest = _vote_dir(workdir, session_id) / f"{vote_id}.json"
        if not manifest.exists():
            return False
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("status") != "open":
            return False
        data.setdefault("ballots", {})[agent_id] = choice
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def get_vote_result(vote_id: str, workdir: str, session_id: str) -> dict | None:
    """Read a previously completed vote result from disk."""
    try:
        result_file = _vote_dir(workdir, session_id) / f"{vote_id}_result.json"
        if result_file.exists():
            return json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def list_votes(workdir: str, session_id: str) -> list[dict]:
    """List all votes for the current session."""
    try:
        vdir = _vote_dir(workdir, session_id)
        results = []
        for f in sorted(vdir.glob("*_result.json")):
            try:
                results.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        return results
    except Exception:
        return []


# ── Internals ─────────────────────────────────────────────────────────────────

def _vote_dir(workdir: str, session_id: str) -> Path:
    return Path(workdir) / "sessions" / session_id / _VOTE_DIR_NAME


def _resolve_agents(agent_ids: list[str] | None, cfg) -> list[str]:
    """Return list of agent IDs to ask. Falls back to registered user-agents."""
    if agent_ids:
        return agent_ids
    try:
        ua_path = Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"
        if ua_path.exists():
            data = json.loads(ua_path.read_text(encoding="utf-8"))
            active = [a["id"] for a in data.get("agents", []) if a.get("active", True)]
            if active:
                return active
    except Exception:
        pass
    # Synthetic peer IDs for demo/testing
    return ["peer-alpha", "peer-beta", "peer-gamma"]


def _peer_vote(vote_id: str, question: str, options: list[str],
               agent_id: str, manifest: Path, cfg, ctx) -> None:
    """Run in a thread: ask a sub-agent to cast its vote."""
    try:
        from .sub_agent import run_sub_agent
        opts_str = " | ".join(f"[{i+1}] {o}" for i, o in enumerate(options))
        task = (
            f"You are participating in a multi-agent vote.\n\n"
            f"Question: {question}\n"
            f"Options: {opts_str}\n\n"
            f"Respond with ONLY the text of your chosen option, nothing else.\n"
            f"Your vote_id={vote_id}, your agent_id={agent_id}"
        )
        result = run_sub_agent("analyst", task, cfg, ctx=ctx)
        # Parse chosen option from result
        choice = _parse_choice(result, options)
        # Write ballot back to manifest
        _write_ballot(manifest, agent_id, choice)
    except Exception:
        pass


def _parse_choice(result: str, options: list[str]) -> str:
    """Find which option the agent chose from its free-text response."""
    r = result.strip().lower()
    # Exact match
    for opt in options:
        if opt.lower() in r:
            return opt
    # Numeric match: "1", "option 2", "[3]"
    import re
    m = re.search(r"\b([1-9])\b", r)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(options):
            return options[idx]
    # Fallback: first option
    return options[0]


def _write_ballot(manifest: Path, agent_id: str, choice: str) -> None:
    """Thread-safe ballot write using read-modify-write with retry."""
    for _ in range(3):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data.setdefault("ballots", {})[agent_id] = choice
            manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        except Exception:
            time.sleep(0.1)


def _tally(vote_id: str, question: str, options: list[str],
           ballots: dict, manifest: Path) -> dict:
    """Count votes and determine winner."""
    from rich.console import Console
    from rich.markup import escape
    _con = Console()

    counts: dict[str, int] = {o: 0 for o in options}
    for agent_id, choice in ballots.items():
        if choice in counts:
            counts[choice] += 1
        else:
            # fuzzy match
            for opt in options:
                if opt.lower() in choice.lower():
                    counts[opt] += 1
                    break

    total   = sum(counts.values())
    winner  = max(counts, key=counts.get) if total > 0 else options[0]
    unanimous = (total > 0 and counts[winner] == total)

    result = {
        "vote_id":   vote_id,
        "question":  question,
        "options":   options,
        "votes":     counts,
        "winner":    winner,
        "total":     total,
        "unanimous": unanimous,
        "ballots":   ballots,
        "completed_at": datetime.utcnow().isoformat(),
    }

    # Persist result
    try:
        result_file = manifest.parent / f"{vote_id}_result.json"
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        # Close manifest
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["status"] = "closed"
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Display results
    _show_results(_con, result)
    return result


def _show_vote_banner(question: str, options: list[str], vote_id: str) -> None:
    from rich.console import Console
    from rich.markup import escape
    _con = Console()
    _con.print()
    _con.print(f"  [bold #ff8c00]╭─ VOTE [{vote_id}] ─────────────────────────────────────╮[/bold #ff8c00]")
    _con.print(f"  [bold #ff8c00]│[/bold #ff8c00]  [white]{escape(question)}[/white]")
    for i, opt in enumerate(options, 1):
        _con.print(f"  [bold #ff8c00]│[/bold #ff8c00]  [dim #888888]{i}.[/dim #888888]  {escape(opt)}")
    _con.print(f"  [bold #ff8c00]│[/bold #ff8c00]  [dim]Опрашиваю агентов…[/dim]")
    _con.print(f"  [bold #ff8c00]╰──────────────────────────────────────────────────────╯[/bold #ff8c00]")
    _con.print()


def _show_results(con, result: dict) -> None:
    from rich.markup import escape
    q       = result["question"]
    winner  = result["winner"]
    total   = result["total"]
    counts  = result["votes"]
    vid     = result["vote_id"]
    con.print()
    con.print(f"  [bold #5fd7af]╭─ VOTE RESULT [{vid}] ─────────────────────────────────╮[/bold #5fd7af]")
    con.print(f"  [bold #5fd7af]│[/bold #5fd7af]  [dim]{escape(q)}[/dim]")
    for opt, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * cnt + "░" * max(0, total - cnt)
        star = "  [bold #ff8c00]← победитель[/bold #ff8c00]" if opt == winner else ""
        con.print(f"  [bold #5fd7af]│[/bold #5fd7af]  {escape(opt):<20} {bar}  {cnt}/{total}{star}")
    tag = "[bold]Единогласно[/bold]" if result["unanimous"] else "[dim]Большинством[/dim]"
    con.print(f"  [bold #5fd7af]│[/bold #5fd7af]  {tag}: [bold white]{escape(winner)}[/bold white]")
    con.print(f"  [bold #5fd7af]╰──────────────────────────────────────────────────────╯[/bold #5fd7af]")
    con.print()


def _trivial_result(question: str, options: list[str]) -> dict:
    winner = options[0] if options else ""
    return {
        "vote_id": "trivial", "question": question, "options": options,
        "votes": {winner: 1}, "winner": winner, "total": 1,
        "unanimous": True, "ballots": {}, "completed_at": datetime.utcnow().isoformat(),
    }

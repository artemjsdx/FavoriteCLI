"""
favorite/token_usage.py — SQLite-based token usage tracker (§30.2).
Tracks per-model token consumption and estimated cost.
"""
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional

_DB_PATH = Path.home() / ".favorite" / "token_usage.db"


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       TEXT    NOT NULL,
            agent_id TEXT    NOT NULL DEFAULT 'main',
            model    TEXT    NOT NULL,
            backend  TEXT    NOT NULL DEFAULT 'unknown',
            prompt_tokens      INTEGER DEFAULT 0,
            completion_tokens  INTEGER DEFAULT 0,
            cost_usd  REAL   DEFAULT 0.0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tu_ts ON token_usage(ts)")
    conn.commit()
    return conn


def record(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    backend: str = "unknown",
    agent_id: str = "main",
    cost_usd: float = 0.0,
) -> None:
    """Record a single API call usage."""
    ts = datetime.utcnow().isoformat()
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO token_usage (ts, agent_id, model, backend, prompt_tokens, completion_tokens, cost_usd) VALUES (?,?,?,?,?,?,?)",
            (ts, agent_id, model, backend, prompt_tokens, completion_tokens, cost_usd),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_summary(period: str = "today") -> list[dict]:
    """
    Get usage summary grouped by model.
    period: 'today' | 'week' | 'month' | 'all'
    """
    try:
        conn = _get_conn()
        today = date.today().isoformat()
        week_start = (date.today()).isoformat()

        if period == "today":
            where = f"WHERE ts >= '{today}'"
        elif period == "week":
            from datetime import timedelta
            ws = (date.today() - timedelta(days=7)).isoformat()
            where = f"WHERE ts >= '{ws}'"
        elif period == "month":
            month_start = date.today().replace(day=1).isoformat()
            where = f"WHERE ts >= '{month_start}'"
        else:
            where = ""

        rows = conn.execute(f"""
            SELECT model, COUNT(*) as requests,
                   SUM(prompt_tokens) as pt,
                   SUM(completion_tokens) as ct,
                   SUM(cost_usd) as total_cost
            FROM token_usage {where}
            GROUP BY model
            ORDER BY total_cost DESC
        """).fetchall()
        conn.close()
        return [
            {
                "model": r[0], "requests": r[1],
                "prompt_tokens": r[2] or 0, "completion_tokens": r[3] or 0,
                "total_tokens": (r[2] or 0) + (r[3] or 0),
                "cost_usd": round(r[4] or 0.0, 4),
            }
            for r in rows
        ]
    except Exception:
        return []


def get_total_cost(period: str = "today") -> float:
    """Get total cost for period."""
    summary = get_summary(period)
    return round(sum(r["cost_usd"] for r in summary), 4)


def reset_all() -> None:
    """Reset all usage data."""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM token_usage")
        conn.commit()
        conn.close()
    except Exception:
        pass

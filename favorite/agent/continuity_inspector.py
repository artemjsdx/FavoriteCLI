"""
favorite/agent/continuity_inspector.py — Continuity Inspector (§25).
Checks if agent response makes progress on the task or got stuck/looped.
"""
import re
from typing import Optional


_LOOP_INDICATORS = [
    "как я уже",
    "как упоминал",
    "как сказал ранее",
    "повторю",
    "снова скажу",
    "к сожалению, я не",
    "я не могу",
    "нет возможности",
    "извините, но я",
    "i cannot",
    "i'm unable to",
    "i don't have access",
    "as i mentioned",
    "as i said",
    "as previously",
]

_PROGRESS_INDICATORS = [
    "готово",
    "выполнено",
    "сделано",
    "создан",
    "записан",
    "запушен",
    "установлен",
    "запущен",
    "протестирован",
    "done",
    "complete",
    "created",
    "updated",
    "pushed",
    "installed",
]


def inspect(response: str, prev_responses: list[str], max_similar: int = 2) -> dict:
    """
    Inspect agent response for signs of looping or stuck state.
    
    Returns:
        {
            "status": "ok" | "warning" | "stuck",
            "reason": str,
            "similarity": float,
        }
    """
    resp_lower = response.lower()
    
    # Check for loop indicators
    loop_count = sum(1 for ind in _LOOP_INDICATORS if ind in resp_lower)
    if loop_count >= 2:
        return {
            "status": "warning",
            "reason": f"Агент повторяет одинаковые отказы ({loop_count} фраз-индикаторов)",
            "similarity": 0.0,
        }

    # Check similarity with recent responses
    if prev_responses:
        last = prev_responses[-1].lower()
        # Simple Jaccard similarity on word sets
        words_curr = set(re.findall(r"\w+", resp_lower))
        words_prev = set(re.findall(r"\w+", last))
        if words_curr and words_prev:
            union = words_curr | words_prev
            inter = words_curr & words_prev
            sim = len(inter) / len(union)
            if sim > 0.85:
                return {
                    "status": "stuck",
                    "reason": f"Ответ почти идентичен предыдущему (сходство {sim:.0%})",
                    "similarity": sim,
                }
            if sim > 0.65 and len(prev_responses) >= 2:
                return {
                    "status": "warning",
                    "reason": f"Высокое сходство с предыдущим ответом ({sim:.0%})",
                    "similarity": sim,
                }

    # Check for progress indicators (good sign)
    progress_count = sum(1 for ind in _PROGRESS_INDICATORS if ind in resp_lower)
    if progress_count >= 1:
        return {"status": "ok", "reason": "прогресс обнаружен", "similarity": 0.0}

    return {"status": "ok", "reason": "", "similarity": 0.0}


def should_interrupt(inspection: dict, consecutive_warnings: int) -> bool:
    """Decide if the agent loop should be interrupted."""
    if inspection["status"] == "stuck":
        return True
    if inspection["status"] == "warning" and consecutive_warnings >= 2:
        return True
    return False

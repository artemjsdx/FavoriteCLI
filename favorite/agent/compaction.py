"""
favorite/agent/compaction.py — Integration point for context compaction in agent loop.
Called automatically when context grows too large.
"""
from pathlib import Path

_MAX_HISTORY_MESSAGES = 60  # compaction threshold
_MAX_HISTORY_CHARS = 80_000  # compaction threshold (chars)


def should_compact(messages: list[dict]) -> bool:
    """Check if history is long enough to warrant compaction."""
    if len(messages) >= _MAX_HISTORY_MESSAGES:
        return True
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    if total_chars >= _MAX_HISTORY_CHARS:
        return True
    return False


def compact_messages(messages: list[dict], session_id: str, workdir: str, cfg=None) -> list[dict]:
    """
    Compact message history by summarizing old messages.
    Keeps the system prompt (index 0) and last 20 messages.
    Inserts a summary as a system message.
    """
    if not messages or len(messages) < 10:
        return messages

    system_msg = messages[0] if messages[0].get("role") == "system" else None
    recent = messages[-20:]

    # Build text of old messages for summarization
    old_messages = messages[1:-20] if system_msg else messages[:-20]
    if not old_messages:
        return messages

    old_text = "\n\n".join(
        f"[{m.get('role','?').upper()}]: {str(m.get('content',''))[:500]}"
        for m in old_messages
    )

    summary = _summarize(old_text, cfg)
    summary_msg = {
        "role": "system",
        "content": f"[CONTEXT SUMMARY — {len(old_messages)} earlier messages compacted]\n{summary}",
    }

    # Save summary to disk
    try:
        sess_dir = Path(workdir) / "sessions" / session_id
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "context_summary.md").write_text(
            f"# Context Summary\n{summary}", encoding="utf-8"
        )
    except Exception:
        pass

    compacted = []
    if system_msg:
        compacted.append(system_msg)
    compacted.append(summary_msg)
    compacted.extend(recent)
    return compacted


def _summarize(text: str, cfg=None) -> str:
    """Summarize old conversation history using LLM."""
    try:
        from .llm import call_llm
        return call_llm(
            system=(
                "Создай максимально краткое и точное резюме истории диалога. "
                "Сохрани: цели, решения, важные факты, текущее состояние задачи. "
                "До 600 слов. Markdown."
            ),
            user=f"История для сжатия:\n{text[:12000]}",
            cfg=cfg,
            model=None,
        )
    except Exception as e:
        return f"[summary unavailable: {e}]\nLast context: {text[-2000:]}"

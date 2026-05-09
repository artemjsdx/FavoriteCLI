"""
favorite/draft.py — Ctrl+S draft saving (§39.2).
Saves in-progress user input before sending, restores on next session start.
"""
from pathlib import Path

_DRAFT_DIR = Path.home() / ".favorite" / "drafts"
_DRAFT_FILE = _DRAFT_DIR / "current_draft.txt"


def save_draft(text: str) -> None:
    """Save current input as draft."""
    _DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    _DRAFT_FILE.write_text(text, encoding="utf-8")


def load_draft() -> str:
    """Load saved draft (or empty string)."""
    if _DRAFT_FILE.exists():
        try:
            return _DRAFT_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return ""


def clear_draft() -> None:
    """Clear draft after successful message send."""
    if _DRAFT_FILE.exists():
        try:
            _DRAFT_FILE.unlink()
        except Exception:
            pass


def archive_draft(session_id: str) -> None:
    """Archive current draft when starting a new session."""
    if _DRAFT_FILE.exists():
        draft_text = load_draft()
        if draft_text:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive = _DRAFT_DIR / f"draft_{ts}_{session_id[:8]}.txt"
            try:
                _DRAFT_FILE.rename(archive)
            except Exception:
                pass


def check_draft_on_startup() -> str | None:
    """Check for saved draft on startup. Returns draft text or None."""
    draft = load_draft()
    if draft and len(draft.strip()) > 0:
        return draft
    return None

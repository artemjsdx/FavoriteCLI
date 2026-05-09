import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def sessions_dir() -> Path:
    d = PROJECT_ROOT / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_dir() -> Path:
    return PROJECT_ROOT / "config"


def resolve_workdir(path: str) -> str:
    p = Path(path).expanduser().resolve()
    return str(p) if p.is_dir() else os.getcwd()

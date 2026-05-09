"""
favorite/vault.py — Vault system (§33).
Secure local storage for secrets: Telegram sessions, API keys, SSH keys, device configs.
"""
import base64
import json
import os
from pathlib import Path
from typing import Any

_VAULT_DIR = Path.home() / ".favorite" / "vault"


def _vault_path(namespace: str, key: str) -> Path:
    safe_ns = namespace.replace("/", "_").replace("..", "").strip("_")
    safe_key = key.replace("/", "_").replace("..", "").strip("_")
    return _VAULT_DIR / safe_ns / (safe_key + ".json")


def _obfuscate(data: str) -> str:
    """Simple base64 obfuscation (not encryption — for display only)."""
    return base64.b64encode(data.encode()).decode()


def _deobfuscate(data: str) -> str:
    try:
        return base64.b64decode(data.encode()).decode()
    except Exception:
        return data


def write(namespace: str, key: str, value: Any, obfuscate: bool = False) -> None:
    """Write a value to vault."""
    path = _vault_path(namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    stored_value = _obfuscate(str(value)) if obfuscate else value
    payload = {
        "value": stored_value,
        "obfuscated": obfuscate,
        "namespace": namespace,
        "key": key,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    # Restrict permissions (Termux — best-effort)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def read(namespace: str, key: str, default: Any = None) -> Any:
    """Read a value from vault."""
    path = _vault_path(namespace, key)
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("value", default)
        if payload.get("obfuscated"):
            return _deobfuscate(value)
        return value
    except Exception:
        return default


def delete(namespace: str, key: str) -> bool:
    """Delete a vault entry."""
    path = _vault_path(namespace, key)
    if path.exists():
        path.unlink()
        return True
    return False


def list_keys(namespace: str) -> list[str]:
    """List all keys in a namespace."""
    ns_dir = _VAULT_DIR / namespace.replace("/", "_")
    if not ns_dir.exists():
        return []
    return [p.stem for p in sorted(ns_dir.glob("*.json"))]


def list_namespaces() -> list[str]:
    """List all namespaces in vault."""
    if not _VAULT_DIR.exists():
        return []
    return [d.name for d in sorted(_VAULT_DIR.iterdir()) if d.is_dir()]


def exists(namespace: str, key: str) -> bool:
    """Check if a vault entry exists."""
    return _vault_path(namespace, key).exists()


def get_all(namespace: str) -> dict[str, Any]:
    """Get all key-value pairs in a namespace."""
    return {k: read(namespace, k) for k in list_keys(namespace)}

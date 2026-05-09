"""
favorite/key_rotation.py — API key rotation (§39.3).
Supports multiple keys per provider with automatic failover on 429/401.
"""
import json
import time
from pathlib import Path
from typing import Optional

_KEYS_FILE = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def _load_keys_config() -> dict:
    if _KEYS_FILE.exists():
        try:
            return json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class KeyRotator:
    """Manages rotation of API keys for a single provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self._keys: list[str] = []
        self._current_idx: int = 0
        self._failures: dict[int, int] = {}  # idx → fail_count
        self._load()

    def _load(self) -> None:
        cfg = _load_keys_config()
        provider_cfg = cfg.get(self.provider, {})
        if isinstance(provider_cfg, str):
            # Single key format
            self._keys = [provider_cfg] if provider_cfg else []
        elif isinstance(provider_cfg, dict):
            rotation = provider_cfg.get("rotation_keys", [])
            primary = provider_cfg.get("key", "")
            if rotation:
                self._keys = [primary] + rotation if primary else rotation
            elif primary:
                self._keys = [primary]
        elif isinstance(provider_cfg, list):
            self._keys = provider_cfg
        self._keys = [k for k in self._keys if k]

    def current_key(self) -> Optional[str]:
        if not self._keys:
            return None
        return self._keys[self._current_idx % len(self._keys)]

    def rotate(self, reason: str = "") -> Optional[str]:
        """Switch to next key. Returns new key or None if no more keys."""
        if len(self._keys) <= 1:
            return None
        self._failures[self._current_idx] = self._failures.get(self._current_idx, 0) + 1
        self._current_idx = (self._current_idx + 1) % len(self._keys)
        import sys
        print(f"[key_rotation] {self.provider}: switched to key [{self._current_idx}]"
              f"{' reason=' + reason if reason else ''}", file=sys.stderr)
        return self.current_key()

    def all_failed(self) -> bool:
        """True if all keys have failed at least once."""
        return len(self._failures) >= len(self._keys) and len(self._keys) > 0

    def reset_failures(self) -> None:
        """Reset failure counters (e.g., after a successful request)."""
        self._failures.clear()

    def status(self) -> list[dict]:
        """Return status of all keys (for /usage display)."""
        result = []
        for i, key in enumerate(self._keys):
            result.append({
                "idx": i,
                "key_hint": key[:8] + "..." + key[-4:] if len(key) > 12 else key,
                "is_current": i == self._current_idx,
                "fail_count": self._failures.get(i, 0),
                "tag": "[ROT]",
            })
        return result


# Module-level singletons
_rotators: dict[str, KeyRotator] = {}


def get_rotator(provider: str) -> KeyRotator:
    if provider not in _rotators:
        _rotators[provider] = KeyRotator(provider)
    return _rotators[provider]


def get_key(provider: str) -> Optional[str]:
    """Get current API key for provider."""
    return get_rotator(provider).current_key()


def handle_error(provider: str, error_code: int) -> Optional[str]:
    """Handle API error — rotate key if applicable. Returns new key or None."""
    if error_code in (401, 429):
        rotator = get_rotator(provider)
        return rotator.rotate(reason=f"HTTP {error_code}")
    return None

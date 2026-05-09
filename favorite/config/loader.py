import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent.parent

def _load(name: str) -> dict:
    path = _BASE / "config" / name
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _save(name: str, data: dict) -> None:
    path = _BASE / "config" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_key_entry(entry, idx: int, provider: str = "") -> dict:
    """Normalize: plain string key -> dict with all expected fields."""
    if isinstance(entry, str):
        return {
            "key": entry,
            "label": f"{provider}{idx + 1}" if provider else f"key{idx + 1}",
            "model": None,
            "role": "main" if idx == 0 else None,
            "is_default": idx == 0,
        }
    if isinstance(entry, dict):
        entry.setdefault("key", "")
        entry.setdefault("label", f"key{idx + 1}")
        entry.setdefault("model", None)
        entry.setdefault("role", None)
        entry.setdefault("is_default", idx == 0)
        return entry
    return {"key": str(entry), "label": f"key{idx + 1}", "model": None, "role": None, "is_default": idx == 0}


class Config:
    def __init__(self):
        self._keys = _load("api_keys.json")
        self._github = _load("github.json")

    # --- GitHub ---
    @property
    def github_token(self) -> str:
        return self._github.get("token", "")

    @property
    def github_owner(self) -> str:
        return self._github.get("owner", "")

    @property
    def github_repo(self) -> str:
        return self._github.get("repo", "FavoriteCLI")

    @property
    def github_branch(self) -> str:
        return self._github.get("branch", "main")

    def set_github(self, token: str, owner: str, repo: str = "FavoriteCLI", branch: str = "main") -> None:
        self._github = {"token": token, "owner": owner, "repo": repo, "branch": branch}
        _save("github.json", self._github)

    # --- FavoriteAPI ---
    @property
    def favorite_api_keys(self) -> list[dict]:
        raw = self._keys.get("favorite_api", [])
        return [_normalize_key_entry(e, i, "fa") for i, e in enumerate(raw)]

    def add_favorite_key(self, key: str, label: str = "", model: str | None = None) -> None:
        keys = self._keys.setdefault("favorite_api", [])
        is_first = len(keys) == 0
        keys.append({"key": key, "label": label or f"key{len(keys)+1}",
                     "model": model, "role": None, "is_default": is_first})
        _save("api_keys.json", self._keys)

    def remove_favorite_key(self, idx: int) -> bool:
        keys = self._keys.get("favorite_api", [])
        if 0 <= idx < len(keys):
            keys.pop(idx)
            _save("api_keys.json", self._keys)
            return True
        return False

    def set_favorite_key_model(self, idx: int, model: str | None) -> bool:
        keys = self._keys.get("favorite_api", [])
        if 0 <= idx < len(keys):
            entry = _normalize_key_entry(keys[idx], idx, "fa")
            entry["model"] = model
            keys[idx] = entry
            _save("api_keys.json", self._keys)
            return True
        return False

    # --- OpenRouter ---
    @property
    def openrouter_keys(self) -> list[dict]:
        raw = self._keys.get("openrouter", [])
        return [_normalize_key_entry(e, i, "or") for i, e in enumerate(raw)]

    # --- NVIDIA ---
    @property
    def nvidia_key(self) -> str:
        return self._keys.get("nvidia_key", "")

    def set_nvidia_key(self, key: str) -> None:
        self._keys["nvidia_key"] = key
        _save("api_keys.json", self._keys)

    def add_openrouter_key(self, key: str, label: str = "", model: str = "qwen/qwen3-coder:free") -> None:
        keys = self._keys.setdefault("openrouter", [])
        is_first = len(keys) == 0
        keys.append({"key": key, "label": label or f"key{len(keys)+1}",
                     "model": model, "role": "main" if is_first else None, "is_default": is_first})
        _save("api_keys.json", self._keys)

    def remove_openrouter_key(self, idx: int) -> bool:
        keys = self._keys.get("openrouter", [])
        if 0 <= idx < len(keys):
            keys.pop(idx)
            _save("api_keys.json", self._keys)
            return True
        return False

    def set_openrouter_model(self, idx: int, model: str) -> bool:
        keys = self._keys.get("openrouter", [])
        if 0 <= idx < len(keys):
            entry = _normalize_key_entry(keys[idx], idx, "or")
            entry["model"] = model
            keys[idx] = entry
            _save("api_keys.json", self._keys)
            return True
        return False

    # --- VoidAI ---
    @property
    def void_ai_key(self) -> str:
        return self._keys.get("void_ai", "")

    def set_void_ai_key(self, key: str) -> None:
        self._keys["void_ai"] = key
        _save("api_keys.json", self._keys)

    # --- FavoriteAPI base URL ---
    @property
    def favorite_api_base_url(self) -> str:
        return self._keys.get("favorite_api_base_url", "http://127.0.0.1:5005")

    def set_favorite_api_base_url(self, url: str) -> None:
        self._keys["favorite_api_base_url"] = url
        _save("api_keys.json", self._keys)

    # --- TG Bridge ---
    @property
    def tg_bridge_token(self) -> str:
        return self._keys.get("tg_bridge", {}).get("token", "")

    @property
    def tg_bridge_chat_id(self) -> str:
        return self._keys.get("tg_bridge", {}).get("chat_id", "")

    def set_tg_bridge(self, bridge_token: str, chat_id: str) -> None:
        self._keys["tg_bridge"] = {"token": bridge_token, "chat_id": chat_id}
        _save("api_keys.json", self._keys)

    def has_tg_bridge(self) -> bool:
        return bool(self.tg_bridge_token and self.tg_bridge_chat_id)

    # --- Helpers ---
    def default_openrouter_key(self) -> dict | None:
        keys = self.openrouter_keys
        for k in keys:
            if k.get("is_default"):
                return k
        return keys[0] if keys else None

    def default_favorite_key(self) -> dict | None:
        keys = self.favorite_api_keys
        for k in keys:
            if k.get("is_default"):
                return k
        return keys[0] if keys else None

    def has_any_provider(self) -> bool:
        if self.openrouter_keys or self.favorite_api_keys:
            return True
        try:
            import json as _json
            ua_file = _BASE / "config" / "user_agents.json"
            if ua_file.exists():
                ua = _json.loads(ua_file.read_text(encoding="utf-8"))
                if ua.get("main", {}).get("api_key"):
                    return True
                for ag in ua.get("agents", []):
                    if ag.get("api_key"):
                        return True
        except Exception:
            pass
        return False

    # --- Skills ---
    def skill_enabled(self, skill_id: str, default: bool = True) -> bool:
        data = _load("skills.json")
        return data.get("enabled", {}).get(skill_id, default)

    def set_skill_enabled(self, skill_id: str, enabled: bool) -> None:
        data = _load("skills.json")
        data.setdefault("enabled", {})[skill_id] = enabled
        _save("skills.json", data)

    def skill_setting(self, skill_id: str, key: str, default: str = "") -> str:
        data = _load("skills.json")
        return data.get("settings", {}).get(skill_id, {}).get(key, default)

    def set_skill_setting(self, skill_id: str, key: str, value: str) -> None:
        data = _load("skills.json")
        data.setdefault("settings", {}).setdefault(skill_id, {})[key] = value
        _save("skills.json", data)


_cfg: Config | None = None

def get_config() -> Config:
    global _cfg
    if _cfg is None:
        _cfg = Config()
    return _cfg

def reload_config() -> Config:
    global _cfg
    _cfg = Config()
    return _cfg

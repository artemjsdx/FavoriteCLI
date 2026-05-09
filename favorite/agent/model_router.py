from __future__ import annotations
import re


class RouterModule:
    COMPLEX_MARKERS = [
        "напиши", "разработай", "проанализируй", "исправь", "реализуй", "спроектируй",
        "write", "develop", "analyze", "fix", "implement", "design",
    ]

    # Default models — user key determines the actual provider
    MODEL_COMPLEX = "minimax/minimax-m2.5"
    MODEL_SIMPLE  = "qwen/qwen3-coder:free"

    @staticmethod
    def classify(text: str) -> str:
        words = text.split()
        if len(words) >= 30:
            return "complex"
        text_lower = text.lower()
        for marker in RouterModule.COMPLEX_MARKERS:
            if marker in text_lower:
                return "complex"
        if "```" in text:
            return "complex"
        return "simple"

    @staticmethod
    def select_model(prompt: str, cfg) -> tuple[str, str, str | None]:
        """
        Returns (provider_name, model_name, api_key).

        Priority:
          0. /agents config (user_agents.json) — highest priority
          1. NVIDIA (if key configured)
          2. OpenRouter — uses model from key config, falls back to
             minimax/minimax-m2.5 (complex) or qwen/qwen3-coder:free (simple)
          3. FavoriteAPI
        """
        import json as _json
        from pathlib import Path as _Path

        # Priority 0: /agents UI config (user_agents.json)
        try:
            ua_file = _Path(__file__).resolve().parent.parent.parent / "config" / "user_agents.json"
            if ua_file.exists():
                ua = _json.loads(ua_file.read_text(encoding="utf-8"))
                main = ua.get("main", {})
                if main.get("active") and main.get("api_key") and main.get("provider"):
                    model = main.get("model") or RouterModule.MODEL_COMPLEX
                    provider = main["provider"].lower().replace("_", "").replace("-", "")
                    key = main["api_key"]
                    if provider in ("favoriteapi", "favorite"):
                        return "FavoriteAPI", model, key
                    elif provider == "openrouter":
                        return "OpenRouter", model, key
                    elif provider == "nvidia":
                        return "NVIDIA", model, key
        except Exception:
            pass

        complexity = RouterModule.classify(prompt)

        # Priority 1: NVIDIA
        nv_key = cfg.nvidia_key
        if nv_key:
            return "NVIDIA", "nvidia/llama-3.1-nemotron-70b-instruct", nv_key

        # Priority 2: OpenRouter
        or_entry = cfg.default_openrouter_key()
        if or_entry:
            key_val = or_entry["key"]
            configured_model = or_entry.get("model", "")
            # If user explicitly set a non-default model, always use it
            if configured_model and configured_model != "qwen/qwen3-coder:free":
                return "OpenRouter", configured_model, key_val
            if complexity == "complex":
                return "OpenRouter", RouterModule.MODEL_COMPLEX, key_val
            return "OpenRouter", RouterModule.MODEL_SIMPLE, key_val

        # Priority 3: FavoriteAPI
        fav_key = cfg.default_favorite_key()
        if fav_key:
            return "FavoriteAPI", fav_key.get("model", "gemini-3.0-flash-thinking"), fav_key["key"]

        raise RuntimeError("No LLM providers configured")

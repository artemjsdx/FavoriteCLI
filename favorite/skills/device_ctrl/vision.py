"""
favorite/skills/device_ctrl/vision.py — анализ скриншота через vision-модель.
"""
import base64
import json
import re
import requests
from . import config as dcfg


_OR_BASE = "https://openrouter.ai/api/v1"
_FA_BASE = "https://api.favoriteapi.ru/v1"  # FavoriteAPI endpoint (adjust if needed)


def _or_vision(b64: str, prompt: str, model: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/artemjsdx/FavoriteCLI",
        "X-Title": "FavoriteCLI-DeviceCtrl",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    r = requests.post(f"{_OR_BASE}/chat/completions", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _fa_vision(b64: str, prompt: str, model: str, api_key: str, base_url: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    r = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _parse_vision_json(text: str) -> dict:
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"description": text, "found": False, "x": None, "y": None}


def analyze_screenshot(b64: str, question: str | None = None) -> dict:
    """
    Отправляет скриншот в vision-модель.
    Возвращает: {"description": str, "found": bool, "x": int|None, "y": int|None, "suggested_action": str}
    """
    cfg = dcfg.load()

    # Определяем модель и провайдера
    vision_model = cfg.get("vision_model")

    # Строим промпт
    extra = cfg.get("vision_prompt_extra", "")
    task_part = f"Найди на экране: {question}." if question else ""
    prompt = (
        f"Ты — анализатор Android-экрана.\n{task_part}\n"
        "Ответь строго в JSON: "
        '{"description": "краткое описание экрана", "found": true/false, '
        '"x": координата_x или null, "y": координата_y или null, '
        '"suggested_action": "рекомендуемое действие"}'
        f"\n{extra}"
    )

    # Загружаем конфиг агентов для получения ключей
    import sys
    from pathlib import Path
    config_dir = Path(__file__).resolve().parents[4] / "config"
    agents_file = config_dir / "user_agents.json"
    or_key = None
    fa_keys = []
    fa_base = None

    if agents_file.exists():
        try:
            ac = json.loads(agents_file.read_text(encoding="utf-8"))
            main = ac.get("main", {})
            provider = main.get("provider", "")
            if provider == "openrouter":
                or_key = main.get("api_key")
            elif provider in ("favoriteapi", "favorite"):
                fa_keys.append(main.get("api_key"))
                fa_base = main.get("base_url", _FA_BASE)
        except Exception:
            pass

    # Fallback ключи
    api_keys_file = config_dir / "api_keys.json"
    if api_keys_file.exists():
        try:
            ak = json.loads(api_keys_file.read_text(encoding="utf-8"))
            if not or_key:
                or_key = ak.get("openrouter") or ak.get("openrouter_api_key")
            fa_from_file = ak.get("favoriteapi_keys", [])
            if fa_from_file:
                fa_keys.extend(fa_from_file)
                fa_base = fa_base or ak.get("favoriteapi_base", _FA_BASE)
        except Exception:
            pass

    # Выбираем метод
    if not vision_model:
        return {"description": "[vision: vision_model не задана. Установи /device vision <модель>]",
                "found": False, "x": None, "y": None}

    last_err = None
    # Пробуем FavoriteAPI ключи
    for fa_key in fa_keys:
        try:
            raw = _fa_vision(b64, prompt, vision_model, fa_key, fa_base or _FA_BASE)
            return _parse_vision_json(raw)
        except Exception as e:
            last_err = e

    # Пробуем OpenRouter
    if or_key:
        try:
            raw = _or_vision(b64, prompt, vision_model, or_key)
            return _parse_vision_json(raw)
        except Exception as e:
            last_err = e

    return {"description": f"[vision ERROR: {last_err}]", "found": False, "x": None, "y": None}


def list_or_vision_models(or_key: str) -> list[dict]:
    """Получить список vision-моделей с OpenRouter."""
    headers = {
        "Authorization": f"Bearer {or_key}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.get(f"{_OR_BASE}/models", headers=headers, timeout=15)
        r.raise_for_status()
        models = r.json().get("data", [])
        vision = []
        for m in models:
            arch = m.get("architecture", {})
            modalities = arch.get("input_modalities", []) or arch.get("modality", "")
            has_vision = "image" in (modalities if isinstance(modalities, list) else [modalities])
            if has_vision:
                vision.append({
                    "id": m.get("id"),
                    "name": m.get("name", m.get("id")),
                    "context": m.get("context_length"),
                })
        return vision
    except Exception:
        return []

"""
favorite/skills/device_ctrl/config.py — загрузка/сохранение конфига device_ctrl.
"""
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "device_ctrl.json"

_DEFAULTS = {
    "enabled": False,
    "devices": [],
    "vision_model": None,
    "vision_prompt_extra": "",
    "screenshot_quality": 80,
    "action_delay_ms": 500,
    "timeout_sec": 15,
    "save_screenshots": True,
    "screenshots_dir": "sessions/{session_id}/device_screens/",
}


def load() -> dict:
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            merged = dict(_DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_default_device(cfg: dict | None = None) -> dict | None:
    c = cfg or load()
    devices = c.get("devices", [])
    for d in devices:
        if d.get("default"):
            return d
    return devices[0] if devices else None


def device_serial(device: dict) -> str:
    ip = device.get("ip", "")
    port = device.get("port", 5555)
    return f"{ip}:{port}"

"""
favorite/skills/device_ctrl/__init__.py - ISkill dla device_ctrl.
FIX-2: добавлен shell:cmd= и ui_dump_full действия.
"""
import re
from ..base import ISkill
from ..registry import SkillRegistry
from . import config as dcfg


class DeviceCtrlSkill(ISkill):
    @property
    def name(self) -> str:
        return "device_ctrl"

    @property
    def enabled(self) -> bool:
        return SkillRegistry.is_enabled("device_ctrl")

    def run(self, args: str, ctx=None, cfg=None) -> str:
        """
        Доступные действия:
          screenshot | screenshot:q=вопрос
          tap:x=540:y=960
          tap_text:text=Войти
          type:text=hello
          type_clear:text=new text
          swipe:x1=300:y1=800:x2=300:y2=300:ms=300
          press:key=back
          wait:ms=1500
          ui_dump           — список кликабельных и текстовых элементов (до 50)
          ui_dump_full      — сырой XML первые 6000 символов
          shell:cmd=...     — FIX-2: произвольная adb shell команда (с правильным -s serial)
          find:text=OK:action=tap
          launch:pkg=com.google.android.gm
          apps | device_info | adb_status
        """
        args = (args or "").strip()
        parts = args.split(":", 1)
        action = parts[0].strip().lower()
        rest = parts[1] if len(parts) > 1 else ""

        def _kv(s: str) -> dict:
            result: dict = {}
            for m in re.finditer(r"(\w+)=([^:]*)", s):
                result[m.group(1)] = m.group(2).strip()
            return result

        kv = _kv(rest)
        body = kv.get("text") or kv.get("q") or kv.get("cmd") or None
        c = dcfg.load()

        from .tags import (
            handle_screenshot, handle_tap, handle_tap_text, handle_type,
            handle_type_clear, handle_swipe, handle_press, handle_wait,
            handle_ui_dump, handle_ui_dump_full, handle_find_element,
            handle_app_launch, handle_app_list, handle_device_info,
            handle_adb_status, handle_adb_shell,
        )

        dispatch = {
            "screenshot":    handle_screenshot,
            "tap":           handle_tap,
            "tap_text":      handle_tap_text,
            "type":          handle_type,
            "type_clear":    handle_type_clear,
            "swipe":         handle_swipe,
            "press":         handle_press,
            "wait":          handle_wait,
            "ui_dump":       handle_ui_dump,
            "ui_dump_full":  handle_ui_dump_full,
            "shell":         handle_adb_shell,
            "find":          handle_find_element,
            "launch":        handle_app_launch,
            "apps":          handle_app_list,
            "device_info":   handle_device_info,
            "adb_status":    handle_adb_status,
        }
        handler = dispatch.get(action)
        if not handler:
            return f"[device_ctrl: неизвестное действие {action}. Доступно: {chr(44).join(dispatch)}]"
        try:
            return handler(kv, body, ctx, c)
        except Exception as e:
            return f"[device_ctrl ERROR] {e}"

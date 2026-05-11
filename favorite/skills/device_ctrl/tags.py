"""
favorite/skills/device_ctrl/tags.py — обработчики ADB-тегов для агента.

Каждый обработчик принимает (args: dict, body: str | None, ctx, cfg) → str
и возвращает строку-результат, которая идёт в контекст следующего шага агента.
"""
import time
from . import config as dcfg
from .adb_client import AdbClient, AdbError
from . import cli_ui as ui


def _get_client(cfg: dict | None = None) -> AdbClient:
    c = cfg or dcfg.load()
    dev = dcfg.get_default_device(c)
    if not dev:
        raise AdbError("Нет настроенных устройств. Добавь через /device connect <ip>")
    serial = dcfg.device_serial(dev)
    timeout = c.get("timeout_sec", 15)
    return AdbClient(serial, timeout)


def _save_history(ctx, action: str, detail: str) -> None:
    try:
        from pathlib import Path
        import json, datetime
        if ctx and hasattr(ctx, "workdir") and hasattr(ctx, "session_id"):
            hist_dir = Path(ctx.workdir) / "sessions" / ctx.session_id / "device_screens"
            hist_dir.mkdir(parents=True, exist_ok=True)
            hist_file = hist_dir / "history.jsonl"
            entry = {"ts": datetime.datetime.now().isoformat(), "action": action, "detail": detail}
            with open(hist_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
def handle_screenshot(args: dict, body, ctx, cfg) -> str:
    ui.print_action("screenshot", "Снимаю экран...")
    try:
        client = _get_client(cfg)
        b64 = client.screenshot_b64()
        question = args.get("find") or args.get("q") or body
        from .vision import analyze_screenshot
        result = analyze_screenshot(b64, question)
        ui.print_vision_result(result)
        _save_history(ctx, "screenshot", result.get("description", "")[:80])
        desc = result.get("description", "")
        found = result.get("found", False)
        x, y = result.get("x"), result.get("y")
        out = f"[SCREENSHOT] {desc}"
        if found and x is not None:
            out += f" | Найдено: x={x} y={y}"
        return out
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[SCREENSHOT ERROR] {e}"


def handle_tap(args: dict, body, ctx, cfg) -> str:
    x = int(args.get("x", 0))
    y = int(args.get("y", 0))
    ui.print_action("tap", f"x={x} y={y}")
    try:
        client = _get_client(cfg)
        client.tap(x, y)
        _save_history(ctx, "tap", f"x={x} y={y}")
        return f"[TAP] x={x} y={y} — выполнено"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[TAP ERROR] {e}"


def handle_tap_text(args: dict, body, ctx, cfg) -> str:
    text = args.get("text", "") or body or ""
    ui.print_action("tap_text", f'"{text}"')
    try:
        client = _get_client(cfg)
        xml = client.ui_dump()
        from .ui_dump import find_by_text
        coords = find_by_text(xml, text)
        if not coords:
            return f"[TAP_TEXT ERROR] Элемент '{text}' не найден в UI dump"
        x, y = coords
        client.tap(x, y)
        _save_history(ctx, "tap_text", f'"{text}" → [{x},{y}]')
        return f"[TAP_TEXT] '{text}' → x={x} y={y} — нажато"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[TAP_TEXT ERROR] {e}"


def handle_type(args: dict, body, ctx, cfg) -> str:
    text = args.get("text", "") or body or ""
    ui.print_action("type", f'"{text[:30]}"')
    try:
        client = _get_client(cfg)
        client.type_text(text)
        _save_history(ctx, "type", f'"{text[:40]}"')
        return f"[TYPE] '{text[:50]}' — введено"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[TYPE ERROR] {e}"


def handle_type_clear(args: dict, body, ctx, cfg) -> str:
    text = args.get("text", "") or body or ""
    ui.print_action("type", f'CLEAR + "{text[:30]}"')
    try:
        client = _get_client(cfg)
        client.clear_field()
        time.sleep(0.3)
        client.type_text(text)
        _save_history(ctx, "type_clear", f'"{text[:40]}"')
        return f"[TYPE_CLEAR] поле очищено, введено: '{text[:50]}'"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[TYPE_CLEAR ERROR] {e}"


def handle_swipe(args: dict, body, ctx, cfg) -> str:
    x1 = int(args.get("x1", 300))
    y1 = int(args.get("y1", 800))
    x2 = int(args.get("x2", 300))
    y2 = int(args.get("y2", 300))
    ms = int(args.get("ms", 300))
    ui.print_action("swipe", f"({x1},{y1})→({x2},{y2}) {ms}мс")
    try:
        client = _get_client(cfg)
        client.swipe(x1, y1, x2, y2, ms)
        _save_history(ctx, "swipe", f"({x1},{y1})→({x2},{y2})")
        return f"[SWIPE] ({x1},{y1})→({x2},{y2}) {ms}мс — выполнено"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[SWIPE ERROR] {e}"


def handle_press(args: dict, body, ctx, cfg) -> str:
    key = args.get("key", "") or body or "back"
    ui.print_action("press", key)
    try:
        client = _get_client(cfg)
        client.press_key(key)
        _save_history(ctx, "press", key)
        return f"[PRESS] key={key} — выполнено"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[PRESS ERROR] {e}"


def handle_wait(args: dict, body, ctx, cfg) -> str:
    ms = int(args.get("ms", 1000))
    ui.print_action("wait", f"{ms}мс")
    time.sleep(ms / 1000)
    return f"[WAIT] {ms}мс — ожидание выполнено"


def handle_ui_dump(args: dict, body, ctx, cfg) -> str:
    ui.print_action("find", "UI dump...")
    try:
        client = _get_client(cfg)
        xml = client.ui_dump()
        from .ui_dump import dump_summary
        summary = dump_summary(xml)
        return f"[UI_DUMP]\n{summary}"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[UI_DUMP ERROR] {e}"


def handle_find_element(args: dict, body, ctx, cfg) -> str:
    text = args.get("text", "") or body or ""
    action = args.get("action", "tap")
    ui.print_action("find", f'"{text}" → {action}')
    try:
        client = _get_client(cfg)
        xml = client.ui_dump()
        from .ui_dump import find_by_text
        coords = find_by_text(xml, text)
        if not coords:
            return f"[FIND_ELEMENT] '{text}' не найден"
        x, y = coords
        if action == "tap":
            client.tap(x, y)
            _save_history(ctx, "find", f'"{text}" → tap [{x},{y}]')
            return f"[FIND_ELEMENT] '{text}' найден [{x},{y}] — нажато"
        return f"[FIND_ELEMENT] '{text}' найден [{x},{y}]"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[FIND_ELEMENT ERROR] {e}"


def handle_app_launch(args: dict, body, ctx, cfg) -> str:
    pkg = args.get("pkg", "") or body or ""
    ui.print_action("launch", pkg)
    try:
        client = _get_client(cfg)
        client.launch_app(pkg)
        _save_history(ctx, "launch", pkg)
        return f"[APP_LAUNCH] {pkg} — запущено"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[APP_LAUNCH ERROR] {e}"


def handle_app_list(args: dict, body, ctx, cfg) -> str:
    ui.print_action("find", "список приложений...")
    try:
        client = _get_client(cfg)
        apps = client.list_apps()
        ui.print_apps_table(apps[:30])
        return f"[APP_LIST] {len(apps)} приложений: {', '.join(apps[:20])}"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[APP_LIST ERROR] {e}"


def handle_device_info(args: dict, body, ctx, cfg) -> str:
    ui.print_action("find", "информация об устройстве...")
    try:
        client = _get_client(cfg)
        info = client.device_info()
        ui.print_device_status(info)
        return f"[DEVICE_INFO] {info['model']} | {info['android']} | {info['resolution']}"
    except AdbError as e:
        ui.print_adb_error(str(e))
        return f"[DEVICE_INFO ERROR] {e}"


def handle_adb_status(args: dict, body, ctx, cfg) -> str:
    c = dcfg.load()
    dev = dcfg.get_default_device(c)
    if not dev:
        return "[ADB_STATUS] Нет настроенных устройств"
    serial = dcfg.device_serial(dev)
    client = AdbClient(serial)
    connected = client.check_connected()
    status = "✓ подключено" if connected else "✗ не доступно"
    return f"[ADB_STATUS] {serial} — {status}"

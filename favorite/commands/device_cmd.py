"""
favorite/commands/device_cmd.py — /device команды (§37).
Управление Android-устройствами через ADB over WiFi.
"""
import os
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.panel import Panel
from .base import ICommand, CommandContext

console = Console()

_O  = "\033[38;2;255;140;0m"
_G  = "\033[38;2;80;200;100m"
_R  = "\033[38;2;190;70;70m"
_GR = "\033[38;2;110;110;110m"
_B  = "\033[1m"
_X  = "\033[0m"
_SEP = f"  {_GR}{'─' * 44}{_X}"


def _p(s: str = "") -> None:
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def _cls() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _load_cfg() -> dict:
    try:
        from favorite.skills.device_ctrl import config as dcfg
        return dcfg.load()
    except Exception:
        return {}


def _save_cfg(cfg: dict) -> None:
    try:
        from favorite.skills.device_ctrl import config as dcfg
        dcfg.save(cfg)
    except Exception as e:
        console.print(f"  [red]Ошибка сохранения конфига: {e}[/red]")


def _get_client(cfg: dict | None = None):
    from favorite.skills.device_ctrl.adb_client import AdbClient, AdbError
    from favorite.skills.device_ctrl import config as dcfg
    c = cfg or dcfg.load()
    dev = dcfg.get_default_device(c)
    if not dev:
        raise AdbError("Нет подключённых устройств. Используй /device connect <ip>")
    serial = dcfg.device_serial(dev)
    return AdbClient(serial, c.get("timeout_sec", 15))


# ─────────────────── Главное меню ─────────────────────────────────────────
def _render_main(cfg: dict) -> None:
    _cls()
    devices = cfg.get("devices", [])
    vision = cfg.get("vision_model") or f"{_GR}не задана{_X}"
    enabled = cfg.get("enabled", False)
    state = f"{_G}ON{_X}" if enabled else f"{_R}OFF{_X}"

    _p()
    _p(f"  {_B}{_O}📱 device_ctrl{_X}  [{state}]")
    _p(_SEP)
    _p()
    _p(f"  {_GR}1.{_X}  Устройства  {_GR}({len(devices)} настроено){_X}")
    _p(f"  {_GR}2.{_X}  Vision-модель  {_GR}:{_X} {_O}{escape(str(vision))}{_X}")
    _p(f"  {_GR}3.{_X}  Проверить соединение  [/device status]")
    _p(f"  {_GR}4.{_X}  Скриншот + описание  [/device screenshot]")
    _p(f"  {_GR}5.{_X}  Список приложений  [/device apps]")
    _p(f"  {_GR}6.{_X}  История действий  [/device history]")
    _p(f"  {_GR}7.{_X}  {'Выключить' if enabled else 'Включить'} скилл")
    _p(f"  {_GR}8.{_X}  Настройки задержки и таймаута")
    _p()
    _p(_SEP)
    _p(f"  {_GR}Выбор (1-8) или Enter → выход:{_X}")
    _p()


def _devices_menu(cfg: dict) -> None:
    while True:
        devices = cfg.get("devices", [])
        _cls()
        _p()
        _p(f"  {_B}{_O}Устройства{_X}")
        _p(_SEP)
        _p()
        if not devices:
            _p(f"  {_GR}Нет устройств. Добавь новое.{_X}")
        for i, d in enumerate(devices, 1):
            default_mark = f" {_G}← default{_X}" if d.get("default") else ""
            _p(f"  {_GR}{i}.{_X}  {_B}{escape(d.get('label', '?'))}{_X}  "
               f"{_GR}|{_X} {escape(d.get('ip', '?'))}:{d.get('port', 5555)}{default_mark}")
        _p()
        _p(_SEP)
        _p(f"  {_GR}[a]{_X} добавить  {_GR}[d<N>]{_X} удалить  {_GR}[def<N>]{_X} по умолч.  {_GR}[Enter]{_X} назад")
        _p()
        try:
            raw = input("  → ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw == "a":
            _add_device(cfg)
        elif raw.startswith("d") and raw[1:].isdigit():
            idx = int(raw[1:]) - 1
            if 0 <= idx < len(devices):
                removed = devices.pop(idx)
                _p(f"  {_G}✓{_X} Удалено: {escape(removed.get('label', '?'))}")
                _save_cfg(cfg)
        elif raw.startswith("def") and raw[3:].isdigit():
            idx = int(raw[3:]) - 1
            if 0 <= idx < len(devices):
                for d in devices:
                    d["default"] = False
                devices[idx]["default"] = True
                _save_cfg(cfg)


def _add_device(cfg: dict) -> None:
    _cls()
    _p()
    _p(f"  {_B}{_O}Добавить устройство{_X}")
    _p(_SEP)
    _p()
    _p(f"  {_GR}Убедись что USB/WiFi-отладка включена на устройстве{_X}")
    _p()
    try:
        label = input("  Имя (напр. 'Samsung A52'): ").strip()
        ip    = input("  IP-адрес: ").strip()
        port  = input("  Порт [5555]: ").strip() or "5555"
        if not label or not ip:
            _p(f"  {_GR}Отменено{_X}")
            return
        new_dev = {
            "id": label.lower().replace(" ", "_"),
            "label": label,
            "ip": ip,
            "port": int(port),
            "default": len(cfg.get("devices", [])) == 0,
        }
        cfg.setdefault("devices", []).append(new_dev)

        # Попытка подключиться сразу
        _p(f"  {_GR}Подключаюсь к {ip}:{port}...{_X}")
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            client = AdbClient.connect(ip, int(port))
            _p(f"  {_G}✓ Подключено!{_X}")
        except Exception as e:
            _p(f"  {_R}Не удалось подключиться: {e}{_X}")
            _p(f"  {_GR}Устройство сохранено, попробуй /device connect {ip} позже{_X}")

        _save_cfg(cfg)
    except (EOFError, KeyboardInterrupt):
        _p(f"  {_GR}Отменено{_X}")


def _vision_menu(cfg: dict) -> None:
    while True:
        _cls()
        _p()
        _p(f"  {_B}{_O}Vision-модель{_X}")
        _p(_SEP)
        _p()
        cur = cfg.get("vision_model") or f"{_GR}не задана{_X}"
        _p(f"  Текущая: {_O}{escape(str(cur))}{_X}")
        _p()
        _p(f"  {_GR}1.{_X}  Ввести вручную")
        _p(f"  {_GR}2.{_X}  Список vision-моделей OpenRouter (онлайн)")
        _p(f"  {_GR}3.{_X}  Сбросить (очистить)")
        _p()
        _p(_SEP)
        _p(f"  {_GR}Выбор или Enter → назад:{_X}")
        _p()
        try:
            raw = input("  → ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw == "1":
            try:
                model = input("  Введи ID модели: ").strip()
                if model:
                    cfg["vision_model"] = model
                    _save_cfg(cfg)
                    _p(f"  {_G}✓ Сохранено: {escape(model)}{_X}")
            except (EOFError, KeyboardInterrupt):
                pass
        elif raw == "2":
            _list_or_vision_models(cfg)
        elif raw == "3":
            cfg["vision_model"] = None
            _save_cfg(cfg)
            _p(f"  {_G}✓ Vision-модель сброшена{_X}")


def _list_or_vision_models(cfg: dict) -> None:
    _p(f"  {_GR}Загружаю список vision-моделей...{_X}")
    # Получаем OR ключ
    or_key = None
    config_dir = Path(__file__).resolve().parents[3] / "config"
    agents_file = config_dir / "user_agents.json"
    if agents_file.exists():
        try:
            ac = json.loads(agents_file.read_text(encoding="utf-8"))
            main = ac.get("main", {})
            if main.get("provider") == "openrouter":
                or_key = main.get("api_key")
        except Exception:
            pass

    if not or_key:
        _p(f"  {_R}OpenRouter ключ не найден в user_agents.json{_X}")
        return

    from favorite.skills.device_ctrl.vision import list_or_vision_models
    models = list_or_vision_models(or_key)
    if not models:
        _p(f"  {_GR}Vision-моделей не найдено{_X}")
        return

    _cls()
    _p()
    _p(f"  {_B}{_O}Vision-модели OpenRouter ({len(models)}){_X}")
    _p(_SEP)
    _p()
    for i, m in enumerate(models[:20], 1):
        _p(f"  {_GR}{i:2d}.{_X}  {_O}{escape(m['id'])}{_X}")
        _p(f"       {_GR}{escape(m['name'])}{_X}")
        _p()
    _p(_SEP)
    _p(f"  {_GR}Введи номер для выбора или Enter → назад:{_X}")
    _p()
    try:
        raw = input("  → ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(models):
                cfg["vision_model"] = models[idx]["id"]
                _save_cfg(cfg)
                _p(f"  {_G}✓ Установлено: {escape(models[idx]['id'])}{_X}")
    except (EOFError, KeyboardInterrupt):
        pass


def _delay_menu(cfg: dict) -> None:
    _cls()
    _p()
    _p(f"  {_B}{_O}Задержка и таймаут{_X}")
    _p(_SEP)
    _p()
    _p(f"  {_GR}1.{_X}  Задержка после действия: {_O}{cfg.get('action_delay_ms', 500)}мс{_X}")
    _p(f"  {_GR}2.{_X}  Таймаут ADB команды: {_O}{cfg.get('timeout_sec', 15)}сек{_X}")
    _p()
    _p(_SEP)
    _p(f"  {_GR}Выбор или Enter → назад:{_X}")
    _p()
    try:
        raw = input("  → ").strip()
        if raw == "1":
            val = input("  Задержка мс [500]: ").strip() or "500"
            cfg["action_delay_ms"] = int(val)
            _save_cfg(cfg)
        elif raw == "2":
            val = input("  Таймаут сек [15]: ").strip() or "15"
            cfg["timeout_sec"] = int(val)
            _save_cfg(cfg)
    except (EOFError, KeyboardInterrupt):
        pass


class DeviceCommand(ICommand):
    name = "/device"
    description = "Управление Android-устройствами через ADB (§37)"
    priority = 85

    def execute(self, args: str, ctx: CommandContext) -> None:
        args = (args or "").strip()
        parts = args.split(None, 1)
        sub = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if not sub:
            self._interactive_menu()
            return

        dispatch = {
            "status":      self._status,
            "connect":     self._connect,
            "disconnect":  self._disconnect,
            "screenshot":  self._screenshot,
            "tap":         self._tap,
            "type":        self._type_text,
            "apps":        self._apps,
            "vision":      self._set_vision,
            "history":     self._history,
            "log":         self._history,
        }
        handler = dispatch.get(sub)
        if handler:
            handler(rest, ctx)
        else:
            console.print(f"  [dim]Неизвестная подкоманда: {sub}[/dim]")
            self._show_help()

    def _interactive_menu(self) -> None:
        cfg = _load_cfg()
        while True:
            _render_main(cfg)
            try:
                raw = input("  → ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if not raw or raw == "q":
                break
            if raw == "1":
                _devices_menu(cfg)
                cfg = _load_cfg()
            elif raw == "2":
                _vision_menu(cfg)
                cfg = _load_cfg()
            elif raw == "3":
                self._status("", None)
                input("\n  Нажми Enter...")
            elif raw == "4":
                self._screenshot("", None)
                input("\n  Нажми Enter...")
            elif raw == "5":
                self._apps("", None)
                input("\n  Нажми Enter...")
            elif raw == "6":
                self._history("", None)
                input("\n  Нажми Enter...")
            elif raw == "7":
                cfg["enabled"] = not cfg.get("enabled", False)
                _save_cfg(cfg)
                from favorite.skills.registry import SkillRegistry
                SkillRegistry.set_enabled("device_ctrl", cfg["enabled"])
            elif raw == "8":
                _delay_menu(cfg)
                cfg = _load_cfg()

    def _show_help(self) -> None:
        console.print()
        console.print("  [dim]Подкоманды:[/dim]")
        console.print("  [dim]  /device               — интерактивное меню[/dim]")
        console.print("  [dim]  /device status         — статус подключения[/dim]")
        console.print("  [dim]  /device connect <ip>   — подключить устройство[/dim]")
        console.print("  [dim]  /device disconnect     — отключить[/dim]")
        console.print("  [dim]  /device screenshot     — скриншот + vision[/dim]")
        console.print("  [dim]  /device tap <x> <y>   — нажать[/dim]")
        console.print("  [dim]  /device type <текст>  — ввести текст[/dim]")
        console.print("  [dim]  /device apps           — список приложений[/dim]")
        console.print("  [dim]  /device vision <модель>— задать vision-модель[/dim]")
        console.print("  [dim]  /device history        — история действий[/dim]")
        console.print()

    def _status(self, args: str, ctx) -> None:
        try:
            client = _get_client()
            info = client.device_info()
            from favorite.skills.device_ctrl.cli_ui import print_device_status
            print_device_status(info)
        except Exception as e:
            console.print(f"  [red]✗ Нет соединения:[/red] {e}")

    def _connect(self, args: str, ctx) -> None:
        parts = args.strip().split()
        if not parts:
            console.print("  [dim]Использование: /device connect <ip> [port][/dim]")
            return
        ip = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 5555
        console.print(f"  Подключаюсь к {ip}:{port}...")
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            client = AdbClient.connect(ip, port)
            cfg = _load_cfg()
            # Обновляем или добавляем устройство
            devices = cfg.get("devices", [])
            serial = f"{ip}:{port}"
            found = False
            for d in devices:
                if d.get("ip") == ip and d.get("port") == port:
                    d["default"] = True
                    found = True
                else:
                    d["default"] = False
            if not found:
                devices.append({"id": serial, "label": serial, "ip": ip, "port": port, "default": True})
            cfg["devices"] = devices
            _save_cfg(cfg)
            console.print(f"  [green]✓[/green] Подключено: [bold]{serial}[/bold]")
        except Exception as e:
            console.print(f"  [red]✗ Ошибка:[/red] {e}")

    def _disconnect(self, args: str, ctx) -> None:
        try:
            cfg = _load_cfg()
            from favorite.skills.device_ctrl import config as dcfg
            from favorite.skills.device_ctrl.adb_client import AdbClient
            dev = dcfg.get_default_device(cfg)
            if dev:
                serial = dcfg.device_serial(dev)
                AdbClient(serial).disconnect()
                console.print(f"  [dim]✓ Отключено: {serial}[/dim]")
            else:
                console.print("  [dim]Нет активных устройств[/dim]")
        except Exception as e:
            console.print(f"  [red]Ошибка отключения: {e}[/red]")

    def _screenshot(self, args: str, ctx) -> None:
        try:
            client = _get_client()
            console.print("  [dim]Снимаю скриншот...[/dim]")
            b64 = client.screenshot_b64()
            question = args.strip() or None
            from favorite.skills.device_ctrl.vision import analyze_screenshot
            from favorite.skills.device_ctrl.cli_ui import print_vision_result
            result = analyze_screenshot(b64, question)
            print_vision_result(result)
        except Exception as e:
            console.print(f"  [red]✗ Ошибка:[/red] {e}")

    def _tap(self, args: str, ctx) -> None:
        parts = args.strip().split()
        if len(parts) < 2:
            console.print("  [dim]Использование: /device tap <x> <y>[/dim]")
            return
        try:
            x, y = int(parts[0]), int(parts[1])
            client = _get_client()
            client.tap(x, y)
            console.print(f"  [green]✓[/green] Нажато: [{x}, {y}]")
        except Exception as e:
            console.print(f"  [red]✗ Ошибка:[/red] {e}")

    def _type_text(self, args: str, ctx) -> None:
        if not args.strip():
            console.print("  [dim]Использование: /device type <текст>[/dim]")
            return
        try:
            client = _get_client()
            client.type_text(args.strip())
            console.print(f"  [green]✓[/green] Введено: {escape(args[:40])}")
        except Exception as e:
            console.print(f"  [red]✗ Ошибка:[/red] {e}")

    def _apps(self, args: str, ctx) -> None:
        try:
            client = _get_client()
            apps = client.list_apps()
            from favorite.skills.device_ctrl.cli_ui import print_apps_table
            print_apps_table(apps[:30])
            console.print(f"  [dim]Всего: {len(apps)} приложений[/dim]")
        except Exception as e:
            console.print(f"  [red]✗ Ошибка:[/red] {e}")

    def _set_vision(self, args: str, ctx) -> None:
        model = args.strip()
        if not model:
            console.print("  [dim]Использование: /device vision <model_id>[/dim]")
            return
        cfg = _load_cfg()
        cfg["vision_model"] = model
        _save_cfg(cfg)
        console.print(f"  [green]✓[/green] Vision-модель: [bold]{escape(model)}[/bold]")

    def _history(self, args: str, ctx) -> None:
        if not ctx:
            console.print("  [dim]История недоступна без активного чата[/dim]")
            return
        try:
            from pathlib import Path
            import json
            hist_file = Path(ctx.workdir) / "sessions" / ctx.session_id / "device_screens" / "history.jsonl"
            if not hist_file.exists():
                console.print("  [dim]История пуста[/dim]")
                return
            entries = [json.loads(l) for l in hist_file.read_text().splitlines() if l.strip()]
            from favorite.skills.device_ctrl.cli_ui import print_history
            print_history(entries)
        except Exception as e:
            console.print(f"  [red]Ошибка чтения истории: {e}[/red]")

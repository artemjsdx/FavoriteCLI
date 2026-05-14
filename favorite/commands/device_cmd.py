"""favorite/commands/device_cmd.py — /device команды.
Управление Android-устройствами через ADB over WiFi.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from .base import ICommand, CommandContext

console = Console()

_O  = "\033[38;2;255;140;0m"
_G  = "\033[38;2;80;200;100m"
_R  = "\033[38;2;190;70;70m"
_GR = "\033[38;2;110;110;110m"
_B  = "\033[1m"
_X  = "\033[0m"
_SEP = f"  {_GR}{chr(9472) * 44}{_X}"


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
        _p(f"  {_R}Ошибка сохранения: {e}{_X}")


def _local_ip_hint() -> str:
    """Попытка определить локальный IP."""
    try:
        r = subprocess.run(["ip", "route", "get", "1"], capture_output=True, text=True, timeout=3)
        for part in r.stdout.split():
            if part.count(".") == 3 and not part.startswith("0"):
                return part
    except Exception:
        pass
    try:
        r = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=3)
        parts = r.stdout.strip().split()
        if parts:
            return parts[0]
    except Exception:
        pass
    return ""


# ─────────────────── Главное меню ─────────────────────────────────────────

def _render_main(cfg: dict) -> None:
    _cls()
    devices = cfg.get("devices", [])
    vision  = cfg.get("vision_model") or f"{_GR}не задана{_X}"
    enabled = cfg.get("enabled", False)
    state   = f"{_G}ON{_X}" if enabled else f"{_R}OFF{_X}"
    _p()
    _p(f"  {_B}{_O}📱 device_ctrl{_X}  [{state}]")
    _p(_SEP)
    _p()
    _p(f"  {_GR}1.{_X}  Устройства  {_GR}({len(devices)} настроено){_X}")
    _p(f"  {_GR}2.{_X}  Vision-модель  {_GR}:{_X} {_O}{escape(str(cfg.get("vision_model") or "не задана"))}{_X}")
    _p(f"  {_GR}3.{_X}  Проверить соединение")
    _p(f"  {_GR}4.{_X}  Скриншот + описание")
    _p(f"  {_GR}5.{_X}  Список приложений")
    _p(f"  {_GR}6.{_X}  История действий")
    _p(f"  {_GR}7.{_X}  {Выключить if enabled else Включить} скилл")
    _p(f"  {_GR}8.{_X}  Задержка и таймаут")
    _p()
    _p(_SEP)
    _p(f"  {_GR}Выбор (1-8) или Enter → выход:{_X}")
    _p()


# ─────────────────── Список устройств ─────────────────────────────────────

def _devices_menu(cfg: dict) -> None:
    while True:
        devices = cfg.get("devices", [])
        _cls()
        _p()
        _p(f"  {_B}{_O}Устройства{_X}")
        _p(_SEP)
        _p()
        if not devices:
            _p(f"  {_GR}Нет устройств. Нажми [a] чтобы добавить.{_X}")
        else:
            for i, d in enumerate(devices, 1):
                mark = f"  {_G}● default{_X}" if d.get("default") else ""
                _p(f"  {_O}{i}.{_X}  {_B}{escape(d.get("label","?"))}{_X}  "
                   f"{_GR}{escape(d.get("ip","?"))}:{d.get("port", 5555)}{_X}{mark}")
        _p()
        _p(_SEP)
        nav = f"{_GR}[a]{_X} добавить"
        if devices:
            nav += f"  {_GR}[1-{len(devices)}]{_X} управлять"
        nav += f"  {_GR}[Enter]{_X} назад"
        _p(f"  {nav}")
        _p()
        try:
            raw = input("  Выбор: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw == "a":
            _add_device(cfg)
            cfg = _load_cfg()
        elif raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(devices):
                _device_submenu(cfg, idx)
                cfg = _load_cfg()


# ─────────────────── Подменю устройства ───────────────────────────────────

def _device_submenu(cfg: dict, idx: int) -> None:
    while True:
        devices = cfg.get("devices", [])
        if idx >= len(devices):
            break
        d = devices[idx]
        _cls()
        _p()
        _p(f"  {_B}{_O}{escape(d.get("label","?"))}{_X}  "
           f"{_GR}{escape(d.get("ip","?"))}:{d.get("port", 5555)}{_X}")
        _p(_SEP)
        _p()
        _p(f"  {_GR}1.{_X}  Проверить соединение")
        _p(f"  {_GR}2.{_X}  Переподключиться")
        _p(f"  {_GR}3.{_X}  Обновить порт {_GR}(если изменился после перезагрузки){_X}")
        if not d.get("default"):
            _p(f"  {_GR}4.{_X}  Сделать устройством по умолчанию")
        _p(f"  {_GR}5.{_X}  Переименовать")
        _p(f"  {_GR}6.{_X}  Удалить")
        _p()
        _p(_SEP)
        _p(f"  {_GR}Выбор или Enter → назад:{_X}")
        _p()
        try:
            raw = input("  Выбор: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break

        if raw == "1":
            _test_device_connection(d)
            try:
                input("  Enter → продолжить...")
            except (EOFError, KeyboardInterrupt):
                pass

        elif raw == "2":
            _reconnect_device(d)
            try:
                input("  Enter → продолжить...")
            except (EOFError, KeyboardInterrupt):
                pass

        elif raw == "3":
            _p()
            _p(f"  {_GR}Текущий порт: {d.get("port", 5555)}{_X}")
            _p(f"  {_GR}Открой Настройки → Для разработчиков → Отладка по Wi-Fi{_X}")
            _p(f"  {_GR}Там виден новый «IP-адрес и порт».{_X}")
            _p()
            try:
                raw_port = input(f"  Новый порт [{d.get("port", 5555)}]: ").strip()
                if raw_port.isdigit():
                    d["port"] = int(raw_port)
                    _save_cfg(cfg)
                    _p(f"  {_G}✓ Порт обновлён → {d["port"]}{_X}")
                    _reconnect_device(d)
            except (EOFError, KeyboardInterrupt):
                pass
            try:
                input("  Enter → продолжить...")
            except (EOFError, KeyboardInterrupt):
                pass

        elif raw == "4" and not d.get("default"):
            for dev in devices:
                dev["default"] = False
            d["default"] = True
            _save_cfg(cfg)
            _p(f"  {_G}✓ Устройство по умолчанию: {escape(d.get("label","?"))}{_X}")

        elif raw == "5":
            try:
                new_label = input(f"  Новое имя [{escape(d.get("label",""))}]: ").strip()
                if new_label:
                    d["label"] = new_label
                    _save_cfg(cfg)
                    _p(f"  {_G}✓ Переименовано{_X}")
            except (EOFError, KeyboardInterrupt):
                pass

        elif raw == "6":
            try:
                confirm = input(f"  Удалить «{escape(d.get("label","?"))}»? [y/N]: ").strip().lower()
                if confirm == "y":
                    devices.pop(idx)
                    _save_cfg(cfg)
                    _p(f"  {_G}✓ Удалено{_X}")
                    break
            except (EOFError, KeyboardInterrupt):
                pass


def _test_device_connection(d: dict) -> None:
    from favorite.skills.device_ctrl.adb_client import AdbClient, AdbError
    from favorite.skills.device_ctrl import config as dcfg
    serial = dcfg.device_serial(d)
    _p(f"  {_GR}Проверяю соединение...{_X}")
    try:
        info = AdbClient(serial).device_info()
        _p(f"  {_G}✓ {escape(info.get("model","?"))} "
           f"| {escape(info.get("android","?"))} "
           f"| {escape(info.get("resolution","?"))}{_X}")
    except AdbError as e:
        err = str(e)
        _p(f"  {_R}✗ {escape(err)}{_X}")
        if "not found" in err.lower():
            _p(f"  {_GR}  → установи: pkg install android-tools{_X}")
        elif "refused" in err.lower() or "cannot connect" in err.lower() or "failed" in err.lower():
            _p(f"  {_GR}  → порт мог измениться. Выбери пункт 3 «Обновить порт».{_X}")
        elif "unauthorized" in err.lower():
            _p(f"  {_GR}  → на экране устройства появился диалог — разреши подключение.{_X}")


def _reconnect_device(d: dict) -> None:
    from favorite.skills.device_ctrl.adb_client import AdbClient, AdbError
    ip   = d.get("ip", "")
    port = d.get("port", 5555)
    _p(f"  {_GR}Подключаюсь к {ip}:{port}...{_X}")
    try:
        AdbClient.connect(ip, port)
        _p(f"  {_G}✓ Подключено!{_X}")
    except AdbError as e:
        _p(f"  {_R}✗ {escape(str(e))}{_X}")
        _p(f"  {_GR}  Порт Wireless Debugging меняется после перезагрузки.{_X}")
        _p(f"  {_GR}  Обнови его через пункт 3 «Обновить порт».{_X}")


# ─────────────────── Добавить устройство — мастер ──────────────────────────

def _add_device(cfg: dict) -> None:
    _cls()
    _p()
    _p(f"  {_B}{_O}Добавить устройство › мастер подключения{_X}")
    _p(_SEP)
    _p()

    # Шаг 1 — инструкция
    _p(f"  {_O}Шаг 1{_X} — включи Беспроводную отладку на телефоне:")
    _p(f"    {_GR}Android 11+ :{_X}  Настройки → Для разработчиков → Беспроводная отладка")
    _p(f"    {_GR}Android 10-  :{_X}  Настройки → Для разработчиков → Отладка по ADB")
    _p()
    _p(f"  {_O}Шаг 2{_X} — найди IP и порт подключения:")
    _p(f"    На {_B}главном экране{_X} «Беспроводной отладки» виден блок:")
    _p(f"    {_B}IP-адрес и порт: 192.168.1.X:XXXXX{_X}")
    _p()

    # Подсказка IP
    hint = _local_ip_hint()
    if hint:
        _p(f"  {_GR}(IP этого устройства скорее всего: {_O}{hint}{_GR}){_X}")
        _p()

    _p(f"  Введи {_B}IP:порт{_X} {_GR}(с главного экрана, напр. {hint or "192.168.1.3"}:41755){_X}:")
    try:
        raw_addr = input("  Выбор: ").strip()
    except (EOFError, KeyboardInterrupt):
        _p(f"  {_GR}Отменено{_X}")
        return
    if not raw_addr:
        _p(f"  {_GR}Отменено{_X}")
        return

    # Разбираем IP:PORT
    if ":" in raw_addr:
        ip, port_s = raw_addr.rsplit(":", 1)
        try:
            main_port = int(port_s)
        except ValueError:
            _p(f"  {_R}Неверный формат порта{_X}")
            return
    else:
        ip = raw_addr
        main_port = 5555

    _p()

    # Шаг 3 — сопряжение (Android 11+)
    _p(f"  {_O}Шаг 3{_X} — сопряжение {_GR}(только Android 11+, пропусти Enter если Android 10-){_X}:")
    _p(f"    На экране «Беспроводная отладка» нажми:")
    _p(f"    {_B}«Подключить с помощью кода подключения»{_X}")
    _p(f"    Там виден IP:ПОРТ и {_B}6-значный код{_X}")
    _p()
    _p(f"  IP:порт сопряжения {_GR}(напр. {ip}:43117, или Enter — пропустить){_X}:")
    try:
        pair_addr = input("  Выбор: ").strip()
    except (EOFError, KeyboardInterrupt):
        pair_addr = ""

    paired = False
    if pair_addr:
        _p(f"  Код сопряжения {_GR}(6 цифр){_X}:")
        try:
            pair_code = input("  Выбор: ").strip()
        except (EOFError, KeyboardInterrupt):
            pair_code = ""

        if pair_code:
            if ":" in pair_addr:
                pair_ip, ps = pair_addr.rsplit(":", 1)
                pair_port = int(ps)
            else:
                pair_ip   = pair_addr
                pair_port = 43117

            _p(f"  {_GR}Сопрягаюсь с {pair_ip}:{pair_port}...{_X}")
            try:
                r = subprocess.run(
                    ["adb", "pair", f"{pair_ip}:{pair_port}", pair_code],
                    capture_output=True, text=True, timeout=30,
                )
                out = (r.stdout + r.stderr).strip()
                if "successfully paired" in out.lower():
                    _p(f"  {_G}✓ Сопряжение успешно!{_X}")
                    paired = True
                else:
                    _p(f"  {_R}✗ Ошибка сопряжения: {escape(out)}{_X}")
                    _p(f"  {_GR}  Пробуем подключиться без сопряжения...{_X}")
            except FileNotFoundError:
                _p(f"  {_R}adb не найден — установи: pkg install android-tools{_X}")
                return
            except Exception as e:
                _p(f"  {_R}Ошибка: {escape(str(e))}{_X}")

    # Шаг 4 — connect
    _p()
    _p(f"  {_GR}Подключаюсь к {ip}:{main_port}...{_X}")
    connected   = False
    label_auto  = f"{ip}:{main_port}"
    try:
        from favorite.skills.device_ctrl.adb_client import AdbClient, AdbError
        client = AdbClient.connect(ip, main_port)
        info   = client.device_info()
        label_auto = info.get("model", "").strip() or label_auto
        _p(f"  {_G}✓ Подключено!  {_GR}{escape(info.get("android",""))} | {escape(info.get("resolution",""))}{_X}")
        connected = True
    except Exception as e:
        _p(f"  {_R}✗ Не удалось: {escape(str(e))}{_X}")
        _p(f"  {_GR}  Устройство сохранено. Попробуй позже через пункт 2 «Переподключиться».{_X}")

    # Имя устройства
    _p()
    _p(f"  Имя {_GR}[Enter = {escape(label_auto)}]{_X}:")
    try:
        label = input("  Выбор: ").strip() or label_auto
    except (EOFError, KeyboardInterrupt):
        label = label_auto

    new_dev = {
        "id":      label.lower().replace(" ", "_")[:20],
        "label":   label,
        "ip":      ip,
        "port":    main_port,
        "default": len(cfg.get("devices", [])) == 0,
    }
    cfg.setdefault("devices", []).append(new_dev)
    _save_cfg(cfg)

    _p()
    if connected:
        _p(f"  {_G}✓ «{escape(label)}» добавлено и подключено!{_X}")
    else:
        _p(f"  {_GR}«{escape(label)}» сохранено.{_X}")
    try:
        input("  Enter → продолжить...")
    except (EOFError, KeyboardInterrupt):
        pass


# ─────────────────── Vision меню ──────────────────────────────────────────

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
        _p(f"  {_GR}2.{_X}  Список vision-моделей OpenRouter")
        _p(f"  {_GR}3.{_X}  Сбросить")
        _p()
        _p(_SEP)
        _p(f"  {_GR}Выбор или Enter → назад:{_X}")
        _p()
        try:
            raw = input("  Выбор: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        if raw == "1":
            try:
                model = input("  ID модели: ").strip()
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
            _p(f"  {_G}✓ Сброшено{_X}")


def _list_or_vision_models(cfg: dict) -> None:
    _p(f"  {_GR}Загружаю список vision-моделей...{_X}")
    or_key = None
    config_dir  = Path(__file__).resolve().parents[3] / "config"
    agents_file = config_dir / "user_agents.json"
    if agents_file.exists():
        try:
            ac   = json.loads(agents_file.read_text(encoding="utf-8"))
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
        _p(f"  {_GR}{i:2d}.{_X}  {_O}{escape(m["id"])}{_X}")
        _p(f"       {_GR}{escape(m["name"])}{_X}")
        _p()
    _p(_SEP)
    _p(f"  {_GR}Введи номер или Enter → назад:{_X}")
    _p()
    try:
        raw = input("  Выбор: ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(models):
                cfg["vision_model"] = models[idx]["id"]
                _save_cfg(cfg)
                _p(f"  {_G}✓ Установлено: {escape(models[idx]["id"])}{_X}")
    except (EOFError, KeyboardInterrupt):
        pass


# ─────────────────── Задержка / таймаут ───────────────────────────────────

def _delay_menu(cfg: dict) -> None:
    _cls()
    _p()
    _p(f"  {_B}{_O}Задержка и таймаут{_X}")
    _p(_SEP)
    _p()
    _p(f"  {_GR}1.{_X}  Задержка после действия: {_O}{cfg.get("action_delay_ms", 500)} мс{_X}")
    _p(f"  {_GR}2.{_X}  Таймаут ADB команды:      {_O}{cfg.get("timeout_sec", 15)} сек{_X}")
    _p()
    _p(_SEP)
    _p(f"  {_GR}Выбор или Enter → назад:{_X}")
    _p()
    try:
        raw = input("  Выбор: ").strip()
        if raw == "1":
            v = input(f"  Задержка мс [{cfg.get("action_delay_ms",500)}]: ").strip()
            if v.isdigit():
                cfg["action_delay_ms"] = int(v)
                _save_cfg(cfg)
        elif raw == "2":
            v = input(f"  Таймаут сек [{cfg.get("timeout_sec",15)}]: ").strip()
            if v.isdigit():
                cfg["timeout_sec"] = int(v)
                _save_cfg(cfg)
    except (EOFError, KeyboardInterrupt):
        pass


# ─────────────────── Command class ────────────────────────────────────────

class DeviceCommand(ICommand):
    name        = "/device"
    description = "Управление Android-устройствами через ADB"
    priority    = 85

    def execute(self, args: str, ctx: CommandContext) -> None:
        args  = (args or "").strip()
        parts = args.split(None, 1)
        sub   = parts[0].lower() if parts else ""
        rest  = parts[1] if len(parts) > 1 else ""

        if not sub:
            self._interactive_menu()
            return

        dispatch = {
            "status":     self._status,
            "connect":    self._connect,
            "pair":       self._pair,
            "disconnect": self._disconnect,
            "screenshot": self._screenshot,
            "tap":        self._tap,
            "type":       self._type_text,
            "apps":       self._apps,
            "vision":     self._set_vision,
            "history":    self._history,
            "log":        self._history,
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
                raw = input("  Выбор: ").strip().lower()
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
                try:
                    input("\n  Нажми Enter...")
                except (EOFError, KeyboardInterrupt):
                    pass
            elif raw == "4":
                self._screenshot("", None)
                try:
                    input("\n  Нажми Enter...")
                except (EOFError, KeyboardInterrupt):
                    pass
            elif raw == "5":
                self._apps("", None)
                try:
                    input("\n  Нажми Enter...")
                except (EOFError, KeyboardInterrupt):
                    pass
            elif raw == "6":
                self._history("", None)
                try:
                    input("\n  Нажми Enter...")
                except (EOFError, KeyboardInterrupt):
                    pass
            elif raw == "7":
                cfg["enabled"] = not cfg.get("enabled", False)
                _save_cfg(cfg)
                try:
                    from favorite.skills.registry import SkillRegistry
                    SkillRegistry.set_enabled("device_ctrl", cfg["enabled"])
                except Exception:
                    pass
            elif raw == "8":
                _delay_menu(cfg)
                cfg = _load_cfg()

    def _show_help(self) -> None:
        console.print()
        lines = [
            "/device                       — интерактивное меню",
            "/device status                — статус подключения",
            "/device connect <ip>:<port>   — подключить устройство",
            "/device pair <ip>:<pp> <code> [<ip>:<port>]  — сопрячь и подключить",
            "/device disconnect            — отключить",
            "/device screenshot [вопрос]   — скриншот + vision",
            "/device tap <x> <y>           — нажать координату",
            "/device type <текст>          — ввести текст",
            "/device apps                  — список приложений",
            "/device vision <model_id>     — задать vision-модель",
            "/device history               — история действий",
        ]
        for l in lines:
            console.print(f"  [dim]{l}[/dim]")
        console.print()

    def _status(self, args: str, ctx) -> None:
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient, AdbError
            from favorite.skills.device_ctrl import config as dcfg
            cfg = _load_cfg()
            dev = dcfg.get_default_device(cfg)
            if not dev:
                console.print("  [dim]Нет устройств. Добавь через /device → Устройства → a[/dim]")
                return
            serial = dcfg.device_serial(dev)
            info   = AdbClient(serial).device_info()
            from favorite.skills.device_ctrl.cli_ui import print_device_status
            print_device_status(info)
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")

    def _connect(self, args: str, ctx) -> None:
        raw = args.strip()
        if not raw:
            console.print("  [dim]Использование: /device connect <ip>:<port>[/dim]")
            return
        if ":" in raw:
            ip, ps = raw.rsplit(":", 1)
            try:
                port = int(ps)
            except ValueError:
                console.print(f"  [red]Неверный порт: {ps}[/red]")
                return
        else:
            ip   = raw
            port = 5555
        console.print(f"  Подключаюсь к {ip}:{port}...")
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            AdbClient.connect(ip, port)
            cfg     = _load_cfg()
            devices = cfg.get("devices", [])
            serial  = f"{ip}:{port}"
            found   = False
            for d in devices:
                if d.get("ip") == ip and d.get("port") == port:
                    d["default"] = True
                    found = True
                else:
                    d["default"] = False
            if not found:
                devices.append({"id": serial, "label": serial,
                                "ip": ip, "port": port, "default": True})
            cfg["devices"] = devices
            _save_cfg(cfg)
            console.print(f"  [green]✓[/green] Подключено: [bold]{serial}[/bold]")
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")

    def _pair(self, args: str, ctx) -> None:
        """/device pair <ip>:<pair_port> <code> [<ip>:<main_port>]"""
        parts = args.strip().split()
        if len(parts) < 2:
            console.print("  [dim]Использование: /device pair <ip>:<pair_port> <code> [<ip>:<main_port>][/dim]")
            return
        pair_addr = parts[0]
        code      = parts[1]
        main_addr = parts[2] if len(parts) > 2 else None

        if ":" not in pair_addr:
            console.print("  [red]Укажи порт сопряжения: ip:port[/red]")
            return
        pair_ip, ps = pair_addr.rsplit(":", 1)
        pair_port   = int(ps)

        console.print(f"  Сопрягаюсь с {pair_ip}:{pair_port}...")
        try:
            r = subprocess.run(
                ["adb", "pair", f"{pair_ip}:{pair_port}", code],
                capture_output=True, text=True, timeout=30,
            )
            out = (r.stdout + r.stderr).strip()
            if "successfully paired" in out.lower():
                console.print("  [green]✓ Сопряжение успешно![/green]")
            else:
                console.print(f"  [red]✗ {escape(out)}[/red]")
                return
        except FileNotFoundError:
            console.print("  [red]adb не найден. Установи: pkg install android-tools[/red]")
            return
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")
            return

        if main_addr:
            self._connect(main_addr, ctx)

    def _disconnect(self, args: str, ctx) -> None:
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            from favorite.skills.device_ctrl import config as dcfg
            cfg = _load_cfg()
            dev = dcfg.get_default_device(cfg)
            if dev:
                AdbClient(dcfg.device_serial(dev)).disconnect()
                console.print(f"  [dim]✓ Отключено: {dcfg.device_serial(dev)}[/dim]")
            else:
                console.print("  [dim]Нет активных устройств[/dim]")
        except Exception as e:
            console.print(f"  [red]Ошибка: {escape(str(e))}[/red]")

    def _screenshot(self, args: str, ctx) -> None:
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            from favorite.skills.device_ctrl import config as dcfg
            cfg    = _load_cfg()
            dev    = dcfg.get_default_device(cfg)
            if not dev:
                console.print("  [dim]Нет устройств[/dim]")
                return
            client = AdbClient(dcfg.device_serial(dev))
            console.print("  [dim]Снимаю скриншот...[/dim]")
            b64    = client.screenshot_b64()
            from favorite.skills.device_ctrl.vision import analyze_screenshot
            from favorite.skills.device_ctrl.cli_ui import print_vision_result
            print_vision_result(analyze_screenshot(b64, args.strip() or None))
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")

    def _tap(self, args: str, ctx) -> None:
        parts = args.strip().split()
        if len(parts) < 2:
            console.print("  [dim]Использование: /device tap <x> <y>[/dim]")
            return
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            from favorite.skills.device_ctrl import config as dcfg
            cfg  = _load_cfg()
            dev  = dcfg.get_default_device(cfg)
            if not dev:
                console.print("  [dim]Нет устройств[/dim]")
                return
            x, y = int(parts[0]), int(parts[1])
            AdbClient(dcfg.device_serial(dev)).tap(x, y)
            console.print(f"  [green]✓[/green] Нажато: [{x}, {y}]")
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")

    def _type_text(self, args: str, ctx) -> None:
        if not args.strip():
            console.print("  [dim]Использование: /device type <текст>[/dim]")
            return
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            from favorite.skills.device_ctrl import config as dcfg
            cfg = _load_cfg()
            dev = dcfg.get_default_device(cfg)
            if not dev:
                console.print("  [dim]Нет устройств[/dim]")
                return
            AdbClient(dcfg.device_serial(dev)).type_text(args.strip())
            console.print(f"  [green]✓[/green] Введено")
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")

    def _apps(self, args: str, ctx) -> None:
        try:
            from favorite.skills.device_ctrl.adb_client import AdbClient
            from favorite.skills.device_ctrl import config as dcfg
            from favorite.skills.device_ctrl.cli_ui import print_apps_table
            cfg  = _load_cfg()
            dev  = dcfg.get_default_device(cfg)
            if not dev:
                console.print("  [dim]Нет устройств[/dim]")
                return
            apps = AdbClient(dcfg.device_serial(dev)).list_apps()
            print_apps_table(apps[:30])
            console.print(f"  [dim]Всего: {len(apps)} приложений[/dim]")
        except Exception as e:
            console.print(f"  [red]✗ {escape(str(e))}[/red]")

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
            hist_file = (Path(ctx.workdir) / "sessions" /
                         ctx.session_id / "device_screens" / "history.jsonl")
            if not hist_file.exists():
                console.print("  [dim]История пуста[/dim]")
                return
            entries = [json.loads(l) for l in hist_file.read_text().splitlines() if l.strip()]
            from favorite.skills.device_ctrl.cli_ui import print_history
            print_history(entries)
        except Exception as e:
            console.print(f"  [red]Ошибка: {escape(str(e))}[/red]")

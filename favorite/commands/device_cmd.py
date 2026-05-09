"""
favorite/commands/device_cmd.py — /device command (§37).
Manage Android device connections via ADB.
"""
import json
import subprocess
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from .base import ICommand, CommandContext

console = Console()
_VAULT_DIR = Path.home() / ".favorite" / "vault" / "devices"


def _list_devices() -> list[dict]:
    devices = []
    if _VAULT_DIR.exists():
        for d in sorted(_VAULT_DIR.iterdir()):
            meta_file = d / "meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    devices.append(meta)
                except Exception:
                    pass
    return devices


def _check_adb_device(serial: str) -> bool:
    try:
        r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        return serial in r.stdout
    except Exception:
        return False


class DeviceCommand(ICommand):
    name = "/device"
    description = "Управление Android-устройствами через ADB (§37)"
    priority = 85

    def execute(self, args: str, ctx: CommandContext) -> None:
        args = (args or "").strip()
        devices = _list_devices()

        if not args or args == "list":
            self._show_list(devices)
        elif args == "add":
            self._add_device()
        elif args.startswith("remove "):
            name = args[7:].strip()
            self._remove_device(name)
        elif args.startswith("shell "):
            cmd = args[6:].strip()
            self._run_shell(cmd, devices)
        else:
            console.print("  [dim]Команды: /device | /device list | /device add | /device remove <имя> | /device shell <cmd>[/dim]")

    def _show_list(self, devices: list[dict]) -> None:
        if not devices:
            console.print("  [dim #666666]Устройств нет. Добавь через /device add[/dim #666666]")
            return
        table = Table(show_header=True, header_style="bold #ff8c00", box=None)
        table.add_column("Имя")
        table.add_column("Serial/IP", style="dim")
        table.add_column("Онлайн", width=8)
        for d in devices:
            serial = d.get("serial", d.get("ip", "?"))
            online = _check_adb_device(serial)
            status = "[green]✓[/green]" if online else "[dim]✗[/dim]"
            table.add_row(escape(d.get("name", "?")), escape(serial), status)
        console.print(table)

    def _add_device(self) -> None:
        console.print()
        console.print("  [bold]Добавить Android-устройство[/bold]")
        console.print("  [dim]Убедись что USB-отладка включена или ADB over Wi-Fi настроен[/dim]")
        try:
            name = input("  Имя устройства: ").strip()
            serial = input("  Serial/IP (из 'adb devices'): ").strip()
            if not name or not serial:
                console.print("  [dim]Отменено[/dim]")
                return
            device_dir = _VAULT_DIR / name.replace(" ", "_")
            device_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "name": name,
                "serial": serial,
                "added_at": __import__("datetime").datetime.utcnow().isoformat(),
            }
            (device_dir / "meta.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            console.print(f"  [dim #666666]✓ Устройство '{escape(name)}' добавлено[/dim #666666]")
        except (EOFError, KeyboardInterrupt):
            console.print("  [dim]Отменено[/dim]")

    def _remove_device(self, name: str) -> None:
        import shutil
        device_dir = _VAULT_DIR / name.replace(" ", "_")
        if not device_dir.exists():
            console.print(f"  [red]Устройство '{name}' не найдено[/red]")
            return
        shutil.rmtree(device_dir)
        console.print(f"  [dim #666666]✓ Устройство '{escape(name)}' удалено[/dim #666666]")

    def _run_shell(self, cmd: str, devices: list[dict]) -> None:
        if not devices:
            console.print("  [red]Нет привязанных устройств[/red]")
            return
        device = devices[0]
        serial = device.get("serial", "")
        try:
            r = subprocess.run(
                ["adb", "-s", serial, "shell", cmd],
                capture_output=True, text=True, timeout=30
            )
            out = (r.stdout or "").strip()
            err = (r.stderr or "").strip()
            if out:
                console.print(f"[dim]{escape(out)}[/dim]")
            if err:
                console.print(f"[red dim]{escape(err)}[/red dim]")
        except Exception as e:
            console.print(f"  [red]ADB ERROR: {e}[/red]")

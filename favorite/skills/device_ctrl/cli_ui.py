"""
favorite/skills/device_ctrl/cli_ui.py — rich-вывод для device_ctrl.
"""
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.panel import Panel

console = Console()

_ACTION_ICONS = {
    "screenshot": "📸",
    "tap": "🖱️",
    "tap_text": "🖱️",
    "type": "⌨️",
    "swipe": "↔️",
    "press": "🔘",
    "launch": "🚀",
    "find": "🔍",
    "wait": "⏳",
}


def print_device_status(info: dict) -> None:
    console.print()
    console.print(Panel(
        f"[bold]Модель:[/bold]  {escape(info.get('model', '?'))}\n"
        f"[bold]Android:[/bold] {escape(info.get('android', '?'))}\n"
        f"[bold]Экран:[/bold]   {escape(info.get('resolution', '?'))}\n"
        f"[bold]Serial:[/bold]  [dim]{escape(info.get('serial', '?'))}[/dim]",
        title="[bold #ff8c00]📱 Устройство[/bold #ff8c00]",
        border_style="#ff8c00",
    ))


def print_adb_error(err: str) -> None:
    console.print()
    msg = escape(str(err))
    hint = ""
    if "not found" in err.lower() or "command not found" in err.lower():
        hint = "\n[dim]Установи ADB: [bold]pkg install android-tools[/bold][/dim]"
    elif "refused" in err.lower() or "cannot connect" in err.lower():
        hint = "\n[dim]Убедись что WiFi-отладка включена и IP верный.[/dim]"
    elif "unauthorized" in err.lower():
        hint = "\n[dim]На устройстве появился диалог разрешения — разреши его.[/dim]"
    console.print(f"  [bold red]ADB ERROR:[/bold red] {msg}{hint}")
    console.print()


def print_action(action: str, detail: str = "") -> None:
    icon = _ACTION_ICONS.get(action.lower(), "▶️")
    console.print(f"  {icon} [dim]{escape(action)}[/dim]  {escape(detail)}")


def print_vision_result(result: dict) -> None:
    desc = result.get("description", "")
    found = result.get("found", False)
    x, y = result.get("x"), result.get("y")
    console.print()
    console.print(f"  [bold #ff8c00]👁 Vision:[/bold #ff8c00] {escape(str(desc))}")
    if found and x is not None:
        console.print(f"  [dim]  Найдено: [{x}, {y}][/dim]")
    console.print()


def print_apps_table(apps: list[str]) -> None:
    table = Table(show_header=True, header_style="bold #ff8c00", box=None)
    table.add_column("Пакет")
    for i, pkg in enumerate(apps, 1):
        table.add_row(f"[dim]{i}[/dim]  {escape(pkg)}")
    console.print(table)


def print_history(history: list[dict]) -> None:
    if not history:
        console.print("  [dim]История пуста[/dim]")
        return
    for entry in history[-20:]:
        icon = _ACTION_ICONS.get(entry.get("action", "").lower(), "▶️")
        ts = entry.get("ts", "")[:16]
        detail = entry.get("detail", "")
        console.print(f"  {icon} [dim]{ts}[/dim]  {escape(detail)}")


def print_connect_success(serial: str) -> None:
    console.print(f"  [green]✓[/green] Подключено: [bold]{escape(serial)}[/bold]")


def print_disconnect(serial: str) -> None:
    console.print(f"  [dim]✓ Отключено: {escape(serial)}[/dim]")

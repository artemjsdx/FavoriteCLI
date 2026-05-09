"""
favorite/commands/mcp_cmd.py — /mcp command (§ОТСЕК 6 MCP support).

Manage Model Context Protocol server connections.
Commands: /mcp list | /mcp add | /mcp remove | /mcp tools | /mcp call
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .base import ICommand, CommandContext
from ..mcp.client import get_mcp_manager

console = Console()


class McpCommand(ICommand):
    name = "/mcp"
    description = "MCP серверы — list/add/remove/tools/call"

    def execute(self, args: list[str], ctx: CommandContext, cfg) -> None:
        mgr = get_mcp_manager()
        sub = args[0] if args else "list"

        if sub == "list":
            self._list(mgr)
        elif sub == "add":
            self._add(mgr, args[1:])
        elif sub == "remove":
            self._remove(mgr, args[1:])
        elif sub == "tools":
            self._tools(mgr, args[1:])
        elif sub == "call":
            self._call(mgr, args[1:])
        elif sub == "connect":
            name = args[1] if len(args) > 1 else ""
            if mgr.connect(name):
                console.print(f"  [green]✓ Подключён к MCP серверу '{name}'[/green]")
            else:
                console.print(f"  [red]✗ Не удалось подключиться к '{name}'[/red]")
        else:
            self._help()

    def _list(self, mgr) -> None:
        servers = mgr.list_servers()
        if not servers:
            console.print("  [dim]Нет MCP серверов. Добавь через /mcp add <name> stdio <command>[/dim]")
            return
        table = Table(border_style="#ff8c00", header_style="bold white")
        table.add_column("Имя"); table.add_column("Транспорт"); table.add_column("Команда/URL"); table.add_column("Статус")
        clients = set(mgr._clients.keys())
        for s in servers:
            cmd = s.command or s.url or "—"
            status = Text("●  подключён", style="green") if s.name in clients else Text("○  отключён", style="dim")
            table.add_row(s.name, s.transport, cmd, status)
        console.print(table)

    def _add(self, mgr, args: list) -> None:
        if len(args) < 3:
            console.print("  Использование: /mcp add <name> stdio <command> [args...]")
            console.print("                /mcp add <name> http <url>")
            return
        name, transport = args[0], args[1]
        if transport == "stdio":
            command = args[2]
            extra_args = args[3:]
            mgr.add_server(name, "stdio", command=command, args=extra_args)
        elif transport == "http":
            url = args[2]
            mgr.add_server(name, "http", url=url)
        else:
            console.print(f"  [red]Неизвестный транспорт: {transport}[/red]")
            return
        console.print(f"  [green]✓ Добавлен MCP сервер '{name}'[/green]")

    def _remove(self, mgr, args: list) -> None:
        name = args[0] if args else ""
        if mgr.remove_server(name):
            console.print(f"  [green]✓ Удалён MCP сервер '{name}'[/green]")
        else:
            console.print(f"  [red]Сервер '{name}' не найден[/red]")

    def _tools(self, mgr, args: list) -> None:
        name = args[0] if args else ""
        if not name:
            all_tools = mgr.all_tools()
            for sname, tools in all_tools.items():
                console.print(f"  [bold #ff8c00]{sname}[/bold #ff8c00]: {len(tools)} инструментов")
                for t in tools:
                    console.print(f"    • {t.name} — {t.description[:60]}")
            return
        if not mgr.connect(name):
            console.print(f"  [red]Не удалось подключиться к '{name}'[/red]"); return
        tools = mgr.list_tools(name)
        if not tools:
            console.print(f"  [dim]Нет инструментов у '{name}'[/dim]"); return
        table = Table(border_style="#ff8c00", header_style="bold white")
        table.add_column("Инструмент"); table.add_column("Описание")
        for t in tools:
            table.add_row(t.name, t.description[:80])
        console.print(table)

    def _call(self, mgr, args: list) -> None:
        if len(args) < 3:
            console.print("  Использование: /mcp call <server> <tool> <json_args>")
            return
        server, tool = args[0], args[1]
        try:
            arguments = __import__("json").loads(" ".join(args[2:]))
        except Exception:
            console.print("  [red]Неверный JSON для аргументов[/red]"); return
        result = mgr.call_tool(server, tool, arguments)
        console.print(f"  [dim]Результат:[/dim]\n{result}")

    def _help(self) -> None:
        console.print("  [bold #ff8c00]/mcp[/bold #ff8c00] — управление MCP серверами")
        console.print("  /mcp list                        — список серверов")
        console.print("  /mcp add <name> stdio <cmd>      — добавить stdio сервер")
        console.print("  /mcp add <name> http <url>       — добавить HTTP сервер")
        console.print("  /mcp remove <name>               — удалить")
        console.print("  /mcp connect <name>              — подключиться")
        console.print("  /mcp tools [name]                — список инструментов")
        console.print("  /mcp call <srv> <tool> <json>    — вызвать инструмент")

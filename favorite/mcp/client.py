"""
favorite/mcp/client.py — MCP client implementation (§ОТСЕК 6).

Connects to MCP servers (stdio or HTTP), lists tools, calls them.
Follows MCP spec: https://spec.modelcontextprotocol.io/
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

console = Console()

_ROOT = Path(__file__).resolve().parent.parent.parent
_MCP_CFG = _ROOT / "config" / "mcp_servers.json"


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPServer:
    name: str
    transport: str           # "stdio" | "http"
    command: Optional[str] = None    # for stdio
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None        # for http
    enabled: bool = True


class MCPClient:
    """Client for a single MCP server (stdio transport)."""

    def __init__(self, server: MCPServer) -> None:
        self.server = server
        self._proc: Optional[subprocess.Popen] = None
        self._tools: List[MCPTool] = []
        self._lock = threading.Lock()
        self._req_id = 0

    def connect(self) -> bool:
        if self.server.transport == "stdio":
            return self._connect_stdio()
        return False

    def _connect_stdio(self) -> bool:
        try:
            cmd = [self.server.command] + self.server.args
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Initialize
            resp = self._rpc("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "FavoriteCLI", "version": "1.0"},
            })
            if resp and not resp.get("error"):
                self._rpc_notify("notifications/initialized", {})
                return True
        except Exception as e:
            console.print(f"  [dim red]MCP connect error ({self.server.name}): {e}[/dim red]")
        return False

    def disconnect(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                self._proc = None
            except Exception:
                pass

    def list_tools(self) -> List[MCPTool]:
        resp = self._rpc("tools/list", {})
        if resp and "result" in resp:
            tools_data = resp["result"].get("tools", [])
            self._tools = [
                MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                )
                for t in tools_data
            ]
        return self._tools

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        resp = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            parts = []
            for item in content:
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "\n".join(parts)
        if resp and "error" in resp:
            return f"[MCP ERROR] {resp['error']}"
        return "[MCP] No response"

    def _rpc(self, method: str, params: dict) -> Optional[dict]:
        if not self._proc:
            return None
        with self._lock:
            self._req_id += 1
            req = {"jsonrpc": "2.0", "id": self._req_id, "method": method, "params": params}
            try:
                line = json.dumps(req) + "\n"
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
                raw = self._proc.stdout.readline()
                return json.loads(raw) if raw else None
            except Exception as e:
                return {"error": str(e)}

    def _rpc_notify(self, method: str, params: dict) -> None:
        if not self._proc:
            return
        req = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            self._proc.stdin.write(json.dumps(req) + "\n")
            self._proc.stdin.flush()
        except Exception:
            pass


class MCPManager:
    """Manages multiple MCP servers."""

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServer] = {}
        self._clients: Dict[str, MCPClient] = {}
        self._load_config()

    def _load_config(self) -> None:
        if _MCP_CFG.exists():
            try:
                data = json.loads(_MCP_CFG.read_text("utf-8"))
                for s in data.get("servers", []):
                    srv = MCPServer(**s)
                    self._servers[srv.name] = srv
            except Exception:
                pass

    def _save_config(self) -> None:
        _MCP_CFG.parent.mkdir(parents=True, exist_ok=True)
        servers_data = []
        for s in self._servers.values():
            d = {"name": s.name, "transport": s.transport, "enabled": s.enabled}
            if s.command:
                d["command"] = s.command
            if s.args:
                d["args"] = s.args
            if s.url:
                d["url"] = s.url
            servers_data.append(d)
        _MCP_CFG.write_text(json.dumps({"servers": servers_data}, indent=2, ensure_ascii=False), "utf-8")

    def add_server(self, name: str, transport: str, command: str = None,
                   args: list = None, url: str = None) -> MCPServer:
        srv = MCPServer(name=name, transport=transport, command=command,
                        args=args or [], url=url)
        self._servers[name] = srv
        self._save_config()
        return srv

    def remove_server(self, name: str) -> bool:
        if name in self._servers:
            if name in self._clients:
                self._clients[name].disconnect()
                del self._clients[name]
            del self._servers[name]
            self._save_config()
            return True
        return False

    def connect(self, name: str) -> bool:
        srv = self._servers.get(name)
        if not srv:
            return False
        client = MCPClient(srv)
        if client.connect():
            self._clients[name] = client
            return True
        return False

    def list_servers(self) -> List[MCPServer]:
        return list(self._servers.values())

    def list_tools(self, server_name: str) -> List[MCPTool]:
        client = self._clients.get(server_name)
        if client:
            return client.list_tools()
        return []

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        client = self._clients.get(server_name)
        if not client:
            if not self.connect(server_name):
                return f"[MCP] Server '{server_name}' not connected"
            client = self._clients.get(server_name)
        return client.call_tool(tool_name, arguments)

    def all_tools(self) -> Dict[str, List[MCPTool]]:
        result = {}
        for name, client in self._clients.items():
            result[name] = client.list_tools()
        return result

    def disconnect_all(self) -> None:
        for c in self._clients.values():
            c.disconnect()
        self._clients.clear()


_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager

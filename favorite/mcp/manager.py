"""
favorite/mcp/manager.py — re-export for backward compat.
"""
from .client import MCPManager, get_mcp_manager

__all__ = ["MCPManager", "get_mcp_manager"]

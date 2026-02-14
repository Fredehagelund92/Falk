"""MCP (Model Context Protocol) server for falk using FastMCP.

Exposes falk's data agent tools as MCP tools so any MCP client
(Cursor, Claude Desktop, other Pydantic AI agents) can query governed metrics.

The server uses FastMCP, a higher-level MCP framework from the Pydantic AI
ecosystem that provides a simpler, more Pythonic API.
"""
from __future__ import annotations

from falk.mcp.server import mcp, run_server

__all__ = ["mcp", "run_server", "server", "tools"]

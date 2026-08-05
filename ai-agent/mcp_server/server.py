from mcp.server.fastmcp import FastMCP

__version__ = "0.1.0"

mcp = FastMCP("geometry-server")

from mcp_server.tools import register_tools

register_tools(mcp)
from mcp.server.fastmcp import FastMCP

from .general import workspace as workspace_tools
from .geometry import (
    common as geometry_common_tools,
    volume as geometry_volume_tools,
    surface as geometry_surface_tools,
)

def register_tools(mcp: FastMCP) -> None:
    workspace_tools.register(mcp)
    geometry_common_tools.register(mcp)
    geometry_volume_tools.register(mcp)
    geometry_surface_tools.register(mcp)

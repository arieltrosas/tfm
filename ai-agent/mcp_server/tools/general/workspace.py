from mcp.server.fastmcp import FastMCP

from common.types import (
    AppState,
    AABB,
)

from ...types import WriteFileResult
from ...common import resolve_within_root
from ...api_client import (
    state,
    workspace_files,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_app_state() -> AppState:
        """
        Fetch the entire centralized application state (AppState).
        Provides metadata about the current workspace directory path, active workspace filenames, and selection volume.
        """
        return await state()

    
    @mcp.tool()
    async def list_workspace_files() -> list[str]:
        """
        Lists all files available in the workspace. The workspace is highly volatile and may change without a reflection in the
        conversation. This tool ALWAYS gives an updated source of truth for the state of the workspace files.
        """
        return await workspace_files()

    
    @mcp.tool()
    async def write_file(filename: str, content: str) -> str:
        """
        Write text content to a file in the workspace.
        Useful for persisting reports, summaries, or other text the agent generates.
        """
        output_path = await resolve_within_root(filename)
        output_path.write_text(content)
        return output_path.name

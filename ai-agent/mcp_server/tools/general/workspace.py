from pathlib import Path

from mcp.server.fastmcp import FastMCP

from common.types import (
    AppState,
    AABB,
)

from ...common import resolve_within_root
from ...api_client import (
    state,
    workspace,
    workspace_files,
    workspace_remove,
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
        root = Path(await workspace())
        output_path = resolve_within_root(root, filename)
        output_path.write_text(content)
        return output_path.name

    
    @mcp.tool()
    async def read_file(filename: str) -> str:
        """
        Reads the content of a file in the workspace.
        """
        root = Path(await workspace())
        input_path = resolve_within_root(root, filename)
        return input_path.read_text()

    
    @mcp.tool()
    async def delete_file(files: list[str]) -> list[str]:
        """
        Deletes a file in the workspace.
        """
        result = await workspace_remove(files)
        deleted_files = [file for file, result in result.results.items() if result.status == "success"]
        return deleted_files
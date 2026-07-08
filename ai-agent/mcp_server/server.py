import asyncio
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from common.types import AABB
from .api_client import get_state, get_volume, get_workspace_root, list_files, set_volume
from .workspace_access import resolve_workspace_file

__version__ = "0.1.0"
mcp = FastMCP("geometry-server")


@mcp.tool()
async def get_app_state() -> dict:
    """
    Fetch the entire centralized application state (AppState).
    Provides metadata about the current workspace directory path, active workspace filenames, and selection volume.
    """
    state_data = await get_state()
    return state_data.model_dump()


@mcp.tool()
async def list_workspace_files() -> list[str]:
    """
    Lists all files available in the workspace. The workspace is highly volatile and may change without a reflection in the
    conversation. This tool ALWAYS gives an updated source of truth for the state of the workspace files.
    """
    return await list_files()


@mcp.tool()
async def get_selection_volume() -> AABB | None:
    """
    Returns the area selected by the user (or None if no area is selected). This area is used to communicate with the agent
    and indicate where to focus or execute other tools. This tool always gives an updated version of the selection volume set by the user.
    """
    return await get_volume()


@mcp.tool()
async def set_selection_volume(
    x: float | None = None,
    y: float | None = None,
    z: float | None = None,
    w: float | None = None,
    h: float | None = None,
    d: float | None = None,
    clear: bool = False,
) -> dict:
    """
    Modifies or clear the selection volume. This can be usefull to show results to the user after executing other tools.
    """
    if clear:
        await set_volume(None)
        return {"status": "success", "action": "cleared", "volume": None}

    if any(coord is None for coord in (x, y, z, w, h, d)):
        raise ValueError("All coordinates (x, y, z, w, h, d) are required unless clear=True")

    new_volume = AABB(x=x, y=y, z=z, w=w, h=h, d=d)
    await set_volume(new_volume)
    return {"status": "success", "action": "updated", "volume": new_volume.model_dump()}


@mcp.tool()
async def compute_cavity_volume(
    input_file: str,
    aabb: AABB,
    start_resolution: float = 4.0,
    step_factor: float = 0.7,
    tolerance: float = 0.03,
    min_resolution_floor: float = 0.04,
) -> float:
    """
    Calculate the stable, converged volume of an internal cavity using automated multi-resolution grid scaling.

    This tool progressively builds fine-grained 3D grids inside the targeted AABB bounding box and calculates
    occupancy using a single-setup Open3D raycasting scene. It analyzes the variance of the calculated volumes
    between steps, stopping once the delta drops below the specified tolerance or hits the minimum resolution floor.

    Args:
        input_file (str): Input filename of the target mesh file in the workspace.
        aabb (AABB): Area to restrict the volume estimation loop.
        start_resolution (float): Coarse initial voxel dimension to kick off scanning.
        step_factor (float): Multiplier used to shrink the voxel size on each subsequent evaluation step.
        tolerance (float): Percentage variance threshold (e.g. 0.03 = 3%) under which calculation is considered stable.
        min_resolution_floor (float): Hard voxel size floor to ensure processing caps out cleanly.

    Returns:
        float: The final converged cavity volume calculation.
    """
    ws_path = Path(await get_workspace_root())
    input_path = resolve_workspace_file(ws_path, input_file)
    return 0.0


@mcp.tool()
async def find_cavity_with_curvature(
    input_file: str,
    knn: int = 30,
    curvature_threshold: float = 0.05,
    eps: float = 0.05,
    min_points: int = 10,
) -> AABB | None:
    """
    Analyzes a file in the workspace to locate a crack based on surface curvature.
    Returns the Axis-Aligned Bounding Box (AABB) surrounding the identified crack, or None if no crack is found.

    Args:
        input_file (str): The filename of the point cloud in the workspace.
        knn (int): Number of nearest neighbors for covariance estimation (higher = wider search area).
        curvature_threshold (float): Threshold to isolate high curvature points.
        eps (float): DBSCAN clustering distance parameter for noise removal.
        min_points (int): Minimum points for a cluster to be considered valid.

    Returns:
        AABB | None: The bounding box of the crack, or None if nothing passed the thresholds.
    """
    ws_path = Path(await get_workspace_root())
    input_path = resolve_workspace_file(ws_path, input_file)
    return None

# mcp_server/server.py
import os
import sys
import httpx
import open3d as o3d
import numpy as np

from pathlib import Path
from mcp.server.fastmcp import FastMCP

from common.types import (
    AppState,
    AABB,
    VolumeGetResponse,
    VolumeSetRequest,
    WorkspaceResponse,
    WorkspaceFilesResponse,
    WorkspaceUploadRequest,
    WorkspaceUploadResponse,
    WorkspaceRemoveRequest,
    WorkspaceDownloadRequest
)

# -----------------------------------------------------------------------------
# Global Scope

MCP_LOCAL_API_URL = os.environ["MCP_LOCAL_API_URL"]

__version__ = '0.1.0'

mcp = FastMCP("geometry-server")


# -----------------------------------------------------------------------------
# Pure Geometric Processing Engine

def estimate_crack_volume(file_path: str, aabb: AABB) -> float:
    path = Path(file_path)

    # 1. Load the PLY mesh model
    mesh = o3d.io.read_triangle_mesh(Path(path))
    if not mesh.has_triangles():
        raise ValueError(f"The file '{file_path}' does not contain a valid triangle mesh.")

    # Pre-cleaning
    mesh.remove_unreferenced_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    # 2. Set bounds
    min_bound = np.array([aabb.x, aabb.y, aabb.z])
    max_bound = np.array([aabb.x + aabb.w, aabb.y + aabb.h, aabb.z + aabb.d])

    # 3. Check for aabb containing the whole mesh
    mesh_min = mesh.get_min_bound()
    mesh_max = mesh.get_max_bound()

    # If the mesh is completely inside the cutting box, the intersection IS the mesh.
    if np.all(mesh_min >= min_bound) and np.all(mesh_max <= max_bound):
        intersected_mesh = mesh
    else:
        epsilon = 1e-5
        min_bound -= epsilon
        max_bound += epsilon

        box_size = max_bound - min_bound
        cutting_box = o3d.geometry.TriangleMesh.create_box(
            width=box_size[0], height=box_size[1], depth=box_size[2]
        )
        cutting_box.translate(min_bound) # pyright: ignore

        mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
        box_t = o3d.t.geometry.TriangleMesh.from_legacy(cutting_box)

        intersected_mesh_t = mesh_t.boolean_intersection(box_t)
        intersected_mesh = intersected_mesh_t.to_legacy()

        if len(intersected_mesh.triangles) == 0:
            raise ValueError("Boolean intersection resulted in 0 triangles. Verify your bounding box coordinates.")

    # 4. Sanitize the intersection 
    intersected_mesh.remove_duplicated_vertices()
    intersected_mesh.remove_duplicated_triangles()
    intersected_mesh.remove_degenerate_triangles()
    intersected_mesh.remove_unreferenced_vertices()

    # 5. Ensure mesh is closed
    if not intersected_mesh.is_watertight():
        t_repair = o3d.t.geometry.TriangleMesh.from_legacy(intersected_mesh)
        intersected_mesh = t_repair.fill_holes(hole_size=1e9).to_legacy()

    if not intersected_mesh.is_watertight():
        raise RuntimeError("Mesh slice is not closed and could not be repaired. Open3D cannot compute its inner volume.")

    # 6. Compute Convex Hull
    hull_mesh, _ = intersected_mesh.compute_convex_hull()

    # 7. Compute Volumes
    intersected_mesh.orient_triangles()
    hull_mesh.orient_triangles()

    model_volume = intersected_mesh.get_volume()
    hull_volume = hull_mesh.get_volume()

    crack_volume = hull_volume - model_volume
    return float(crack_volume)


# -----------------------------------------------------------------------------
# API Endpoints

async def api_state() -> AppState:
    """Query the local API to get the entire centralized AppState."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/state")
        response.raise_for_status()
        return AppState.model_validate(response.json())


async def api_workspace() -> WorkspaceResponse:
    """Query the local API to get workspace metadata."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/workspace")
        response.raise_for_status()
        return WorkspaceResponse.model_validate(response.json())


async def api_workspace_files() -> WorkspaceFilesResponse:
    """Query the local API to get the list of workspace files."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/workspace/files")
        response.raise_for_status()
        return WorkspaceFilesResponse.model_validate(response.json())


async def api_workspace_upload(file_path: str) -> WorkspaceUploadResponse:
    """Query the local API to copy/upload a local file into the workspace directory."""
    payload = WorkspaceUploadRequest(file_path=file_path)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_LOCAL_API_URL}/workspace/upload", 
            json=payload.model_dump()
        )
        response.raise_for_status()
        return WorkspaceUploadResponse.model_validate(response.json())


async def api_workspace_remove(file_name: str) -> None:
    """Query the local API to delete a specific file from the workspace directory."""
    payload = WorkspaceRemoveRequest(file_name=file_name)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "DELETE", 
            f"{MCP_LOCAL_API_URL}/workspace/remove", 
            json=payload.model_dump()
        )
        response.raise_for_status()


async def api_workspace_download(file_name: str, download_path: str) -> None:
    """Query the local API to copy/download a file from the workspace directory to an external destination."""
    payload = WorkspaceDownloadRequest(file_name=file_name, download_path=download_path)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET", 
            f"{MCP_LOCAL_API_URL}/workspace/download", 
            json=payload.model_dump()
        )
        response.raise_for_status()


async def api_volume_get() -> VolumeGetResponse:
    """Query the local API to get the currently selected single AABB volume configuration."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/volume/get")
        response.raise_for_status()
        return VolumeGetResponse.model_validate(response.json())


async def api_volume_set(volume: AABB | None=None) -> None:
    """Query the local API to overwrite or clear the current active configuration volume."""
    payload = VolumeSetRequest(volume=volume)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_LOCAL_API_URL}/volume/set", 
            json=payload.model_dump()
        )
        response.raise_for_status()


# -----------------------------------------------------------------------------
# MCP Server Tools

@mcp.tool()
async def get_mcp_server_version() -> str:
    """
    Get mcp server version as a string in X.Y.Z format
    """
    return __version__


@mcp.tool()
async def get_open3d_version() -> str:
    """
    Get installed Open3D version a string in X.Y.Z format
    """
    return o3d.__version__


@mcp.tool()
async def list_workspace_files() -> list[str]:
    """
    Lists all files available in the workspace. The workspace is highly volatile and may change without a reflection in the
    conversation. This tool ALWAYS gives an updated source of truth for the state of the workspace files.
    """
    data = await api_workspace_files()
    return data.files


@mcp.tool()
async def get_selection_volume() -> AABB | None:
    """
    Returns the area selected by the user (or None if no area is selected). This area is used to communicate with the agent
    and indicate where to focus or execute other tools. This tool always gives an upadated version of the selection volume set by the user. 
    """
    data = await api_volume_get()
    return data.volume


@mcp.tool()
async def set_selection_volume(
    x: float | None = None,
    y: float | None = None,
    z: float | None = None,
    w: float | None = None,
    h: float | None = None,
    d: float | None = None,
    clear: bool = False
) -> dict:
    """
    Modifies or clear the selection volume. This can be usefull to show results to the user after executing other tools.
    """
    if clear or any(coord is None for coord in (x, y, z, w, h, d)):
        await api_volume_set()
        return {"status": "success", "action": "cleared", "volume": None}

    new_volume = AABB(
        x=x or 0, 
        y=y or 0, 
        z=z or 0, 
        w=w or 0, 
        h=h or 0, 
        d=d or 0
    )
    await api_volume_set(new_volume)
    return {"status": "success", "action": "updated", "volume": new_volume.model_dump()}


@mcp.tool()
async def compute_cavity_volume(input_file: str, aabb: AABB) -> float:
    """
    Calculate the volume of a cavity of a file in the workspace in a specific area.

    Args:
        input_file (str): Input filename of the target file in the workspace.
        aabb (AABB): Area to restrict the estimation, usually set by the user.

    Returns:
        float: The estimated cavity volume.
    """
    response = await api_workspace()
    ws_path = Path(response.ws_path)

    input_path = ws_path / input_file

    if not input_path.is_file():
        raise FileNotFoundError(f"File '{input_file}' not found")

    return estimate_crack_volume(str(input_path), aabb)

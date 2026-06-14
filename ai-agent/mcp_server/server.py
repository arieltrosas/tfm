# mcp_server/server.py
import os
import sys
import time
import httpx
import open3d as o3d
import numpy as np
from scipy import ndimage
from pathlib import Path
from typing import Tuple, cast
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

def estimate_cavity_volume_at_resolution(
    scene: o3d.t.geometry.RaycastingScene,
    aabb: AABB,
    resolution: float,
) -> float:
    min_bound = np.array([aabb.x, aabb.y, aabb.z])
    max_bound = np.array([aabb.x + aabb.w, aabb.y + aabb.h, aabb.z + aabb.d])

    x_coords = np.arange(min_bound[0] - resolution, max_bound[0] + resolution, resolution)
    y_coords = np.arange(min_bound[1] - resolution, max_bound[1] + resolution, resolution)
    z_coords = np.arange(min_bound[2] - resolution, max_bound[2] + resolution, resolution)

    if len(x_coords) <= 2 or len(y_coords) <= 2 or len(z_coords) <= 2:
        return 0.0

    grid_x, grid_y, grid_z = np.meshgrid(x_coords, y_coords, z_coords, indexing="ij")
    query_points = np.stack([grid_x, grid_y, grid_z], axis=-1).astype(np.float32)
    grid_shape = query_points.shape[:-1]

    query_points_flattened = query_points.reshape(-1, 3)
    query_tensor = o3d.core.Tensor(query_points_flattened)

    occupancy_flat = scene.compute_occupancy(query_tensor).numpy()
    is_wall = occupancy_flat.reshape(grid_shape) > 0.5

    air_mask = ~is_wall
    structure = ndimage.generate_binary_structure(3, 1)
    
    try:
        labeled_mask, _ = cast(
            Tuple[np.ndarray, int], ndimage.label(air_mask, structure=structure)
        )
    except Exception as e:
        raise RuntimeError(f"SciPy 3D labeling operation failed: {e}")

    outside_label = labeled_mask[0, 0, 0]
    is_cavity = air_mask & (labeled_mask != outside_label) & (labeled_mask > 0)

    cavity_voxel_count = int(np.sum(is_cavity))
    voxel_volume = resolution**3
    
    return float(cavity_voxel_count * voxel_volume)


def find_converged_cavity_volume(
    file_path: str,
    aabb: AABB,
    start_resolution: float = 4.0,
    step_factor: float = 0.7,
    tolerance: float = 0.03,
    min_resolution_floor: float = 0.04,
) -> float:
    path = Path(file_path)
    mesh = o3d.io.read_triangle_mesh(path)
    if not mesh.has_triangles():
        raise ValueError(f"The file '{file_path}' does not contain a valid triangle mesh.")

    mesh.remove_unreferenced_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    scene = o3d.t.geometry.RaycastingScene()
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    _ = scene.add_triangles(mesh_t)
    
    current_res = start_resolution
    prev_volume = -1.0

    while current_res >= min_resolution_floor:
        current_volume = estimate_cavity_volume_at_resolution(scene, aabb, current_res)
        
        if prev_volume >= 0.0:
            if prev_volume == 0.0:
                variance = float("inf") if current_volume > 0.0 else 0.0
            else:
                variance = abs(current_volume - prev_volume) / prev_volume
        else:
            variance = float("inf")

        if variance <= tolerance and current_volume > 0.0 and prev_volume > 0.0:
            return current_volume

        prev_volume = current_volume
        current_res *= step_factor

    return prev_volume


def find_cavity_aabb(
    file_path: str, 
    knn: int = 30, 
    curvature_threshold: float = 0.05,
    eps: float = 0.05,
    min_points: int = 10
) -> AABB | None:
    input_path = Path(file_path)

    pcd = o3d.io.read_point_cloud(input_path)
    if pcd.is_empty():
        raise ValueError(f"Could not load point cloud from {str(input_path)}")

    search_param = o3d.geometry.KDTreeSearchParamKNN(knn=knn)
    pcd.estimate_covariances(search_param)

    covariances = np.asarray(pcd.covariances)
    eigenvalues = np.linalg.eigvalsh(covariances)

    curvature = eigenvalues[:, 0] / (np.sum(eigenvalues, axis=1) + 1e-6)

    crack_indices = np.where(curvature > curvature_threshold)[0]
    if len(crack_indices) == 0:
        return None
    
    crack_pcd = pcd.select_by_index(crack_indices) # pyright: ignore

    labels = np.array(crack_pcd.cluster_dbscan(eps=eps, min_points=min_points, print_progress=False))
    valid_labels = labels[labels >= 0]
    
    if len(valid_labels) == 0:
        return None

    largest_cluster_idx = np.argmax(np.bincount(valid_labels))
    final_crack_pcd = crack_pcd.select_by_index(np.where(labels == largest_cluster_idx)[0]) # pyright: ignore

    o3d_aabb = final_crack_pcd.get_axis_aligned_bounding_box()

    min_bound = np.array(o3d_aabb.get_min_bound())
    extent = np.array(o3d_aabb.get_extent())

    return AABB(
        x=float(min_bound[0]),
        y=float(min_bound[1]),
        z=float(min_bound[2]),
        w=float(extent[0]),
        h=float(extent[1]),
        d=float(extent[2])
    )


# -----------------------------------------------------------------------------
# API Endpoints

async def api_state() -> AppState:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/state")
        response.raise_for_status()
        return AppState.model_validate(response.json())


async def api_workspace() -> WorkspaceResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/workspace")
        response.raise_for_status()
        return WorkspaceResponse.model_validate(response.json())


async def api_workspace_files() -> WorkspaceFilesResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/workspace/files")
        response.raise_for_status()
        return WorkspaceFilesResponse.model_validate(response.json())


async def api_workspace_upload(file_path: str) -> WorkspaceUploadResponse:
    payload = WorkspaceUploadRequest(file_path=file_path)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_LOCAL_API_URL}/workspace/upload", 
            json=payload.model_dump()
        )
        response.raise_for_status()
        return WorkspaceUploadResponse.model_validate(response.json())


async def api_workspace_remove(file_name: str) -> None:
    payload = WorkspaceRemoveRequest(file_name=file_name)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "DELETE", 
            f"{MCP_LOCAL_API_URL}/workspace/remove", 
            json=payload.model_dump()
        )
        response.raise_for_status()


async def api_workspace_download(file_name: str, download_path: str) -> None:
    payload = WorkspaceDownloadRequest(file_name=file_name, download_path=download_path)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET", 
            f"{MCP_LOCAL_API_URL}/workspace/download", 
            json=payload.model_dump()
        )
        response.raise_for_status()


async def api_volume_get() -> VolumeGetResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/volume/get")
        response.raise_for_status()
        return VolumeGetResponse.model_validate(response.json())


async def api_volume_set(volume: AABB | None=None) -> None:
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
async def get_app_state() -> dict:
    """
    Fetch the entire centralized application state (AppState). 
    Provides metadata about the current workspace directory path, active workspace filenames, and selection volume.
    """
    state_data = await api_state()
    return state_data.model_dump()


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
async def compute_cavity_volume(
    input_file: str, 
    aabb: AABB, 
    start_resolution: float = 4.0,
    step_factor: float = 0.7,
    tolerance: float = 0.03,
    min_resolution_floor: float = 0.04
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
    response = await api_workspace()
    ws_path = Path(response.ws_path)
    input_path = ws_path / input_file

    if not input_path.is_file():
        raise FileNotFoundError(f"File '{input_file}' not found")

    return find_converged_cavity_volume(
        file_path=str(input_path),
        aabb=aabb,
        start_resolution=start_resolution,
        step_factor=step_factor,
        tolerance=tolerance,
        min_resolution_floor=min_resolution_floor
    )


@mcp.tool()
async def find_cavity_with_curvature(
    input_file: str,
    knn: int = 30,
    curvature_threshold: float = 0.05,
    eps: float = 0.05,
    min_points: int = 10
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
    response = await api_workspace()
    ws_path = Path(response.ws_path)
    input_path = ws_path / input_file

    if not input_path.is_file():
        raise FileNotFoundError(f"File '{input_file}' not found in workspace.")

    return find_cavity_aabb(
        file_path=str(input_path),
        knn=knn,
        curvature_threshold=curvature_threshold,
        eps=eps,
        min_points=min_points
    )

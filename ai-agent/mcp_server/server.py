# mcp-server/server.py

import os, sys
import open3d as o3d
import numpy as np

from pathlib import Path

from mcp.server.fastmcp import FastMCP

# -----------------------------------------------------------------------------
# Global Scope

WORKSPACE_DIR = ""

__version__ = '0.1.0'

mcp = FastMCP("geometry-server")


# -----------------------------------------------------------------------------
# MCP Server

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
async def get_workspace_files() -> list[str]:
    """
    Returns a list with the file currently in the workspace.
    """
    ws_path = Path(WORKSPACE_DIR)
    return [path.name for path in ws_path.iterdir() if path.is_file()]


@mcp.tool()
async def point_cloud_get_aabb(input_file: str) -> o3d.geometry.AxisAlignedBoundingBox:
    """
    Returns the Axis Aligned Bounding Box of a point cloud.

    Arguments:
        input_file: File name of the input file in the workspace.

    Returns:
        Axis Aligned Bounding Box encapsulating the point cloud.
    """
    ws_path = Path(WORKSPACE_DIR)
    input_path = ws_path / input_file

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    pcd = o3d.io.read_point_cloud(input_path)
    aabb = pcd.get_axis_aligned_bounding_box()
    return aabb


@mcp.tool()
async def point_cloud_downsample(
    input_file: str, 
    output_file: str,
    levels: int = 1
) -> None:
    """
    Downsamples a point cloud using voxel grid downsampling.

    Arguments:
        input_file: File name of the input file in the workspace
        output_file: File name of the output file in the workspace
        levels: Number of levels of downsampling (1-10+). The greater the number, 
                the larger the voxels and the more aggressive the downsampling.
    """
    ws_path = Path(WORKSPACE_DIR)
    input_path = ws_path / input_file
    output_path = ws_path / output_file

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")
    if levels <= 0:
        raise ValueError("Levels must be a positive integer greater than 0.")

    pcd = o3d.io.read_point_cloud(input_path)
    if pcd.is_empty():
        raise ValueError(f"Failed to parse or empty point cloud: {input_file}")

    extent = pcd.get_axis_aligned_bounding_box().get_max_extent()
    aabb = pcd.get_axis_aligned_bounding_box()
    voxel_size = extent * 0.005 * levels

    downsampled = pcd.voxel_down_sample(voxel_size=voxel_size)

    tmp_p = output_path.with_name(f".tmp_{output_path.name}")
    
    if not o3d.io.write_point_cloud(tmp_p, downsampled):
        raise IOError(f"Open3D failed to write to path: {output_path}")

    tmp_p.replace(output_path)


@mcp.tool()
async def point_cloud_get_info(input_file: str) -> dict:
    """
    Returns basic information and statistics about a point cloud.

    Arguments:
        input_file: File name of the input file in the workspace.

    Returns:
        A dictionary containing the number of points, and boolean flags 
        indicating if the point cloud contains normals or colors.
    """
    ws_path = Path(WORKSPACE_DIR)
    input_path = ws_path / input_file

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    pcd = o3d.io.read_point_cloud(input_path)
    if pcd.is_empty():
        raise ValueError(f"Failed to parse or empty point cloud: {input_file}")

    return {
        "num_points": len(pcd.points),
        "has_normals": pcd.has_normals(),
        "has_colors": pcd.has_colors()
    }


@mcp.tool()
async def point_cloud_estimate_normals(
    input_file: str, 
    output_file: str, 
    radius: float = 0.1, 
    max_nn: int = 30
) -> None:
    """
    Estimates normals for a point cloud and saves the result. Useful for testing
    tools that mutate and save state.

    Arguments:
        input_file: File name of the input file in the workspace
        output_file: File name of the output file in the workspace
        radius: Search radius for normal estimation
        max_nn: Maximum number of nearest neighbors to consider
    """
    ws_path = Path(WORKSPACE_DIR)
    input_path = ws_path / input_file
    output_path = ws_path / output_file

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    pcd = o3d.io.read_point_cloud(input_path)
    if pcd.is_empty():
        raise ValueError(f"Failed to parse or empty point cloud: {input_file}")

    # Estimate normals using hybrid search
    search_param = o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
    pcd.estimate_normals(search_param=search_param)

    tmp_p = output_path.with_name(f".tmp_{output_path.name}")
    
    if not o3d.io.write_point_cloud(tmp_p, pcd):
        raise IOError(f"Open3D failed to write to path: {output_path}")

    tmp_p.replace(output_path)


@mcp.tool()
async def point_cloud_transform(
    input_file: str, 
    output_file: str, 
    tx: float = 0.0, 
    ty: float = 0.0, 
    tz: float = 0.0,
    rx: float = 0.0,
    ry: float = 0.0,
    rz: float = 0.0,
    scale: float = 1.0
) -> None:
    """
    Applies a generic linear transformation (rotation, scaling, translation) to a point cloud.

    Arguments:
        input_file: File name of the input file in the workspace
        output_file: File name of the output file in the workspace
        tx, ty, tz: Translation along the X, Y, and Z axes
        rx, ry, rz: Rotation angles around the X, Y, and Z axes (in degrees)
        scale: Uniform scaling factor
    """
    ws_path = Path(WORKSPACE_DIR)
    input_path = ws_path / input_file
    output_path = ws_path / output_file

    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    pcd = o3d.io.read_point_cloud(input_path)
    if pcd.is_empty():
        raise ValueError(f"Failed to parse or empty point cloud: {input_file}")

    # 1. Convert rotation angles from degrees to radians
    rad_x = np.radians(rx)
    rad_y = np.radians(ry)
    rad_z = np.radians(rz)

    # 2. Calculate individual rotation matrices
    Rx = np.array([[1, 0, 0], [0, np.cos(rad_x), -np.sin(rad_x)], [0, np.sin(rad_x), np.cos(rad_x)]])
    Ry = np.array([[np.cos(rad_y), 0, np.sin(rad_y)], [0, 1, 0], [-np.sin(rad_y), 0, np.cos(rad_y)]])
    Rz = np.array([[np.cos(rad_z), -np.sin(rad_z), 0], [np.sin(rad_z), np.cos(rad_z), 0], [0, 0, 1]])
    
    # Combined rotation matrix (intrinsic XYZ order)
    R = Rz @ Ry @ Rx

    # 3. Construct the 4x4 homogeneous transformation matrix
    T = np.eye(4, dtype=np.float64)
    T[0:3, 0:3] = R * scale  # Apply rotation and scaling
    T[0:3, 3] = [tx, ty, tz]  # Apply translation

    # 4. Transform the point cloud
    pcd.transform(T)  # pyright: ignore

    # 5. Atomic write out to disk
    tmp_p = output_path.with_name(f".tmp_{output_path.name}")
    if not o3d.io.write_point_cloud(tmp_p, pcd):
        raise IOError(f"Open3D failed to write to path: {output_path}")

    tmp_p.replace(output_path)

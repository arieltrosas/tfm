import numpy as np
import open3d as o3d

from geometry.types import Tensor, AABB, TriangleMesh, mesh_to_tensor, mesh_to_legacy
from geometry.io import write_triangle_mesh, write_point_cloud
from geometry.voxelizer import voxelize_mesh


def crop_voxel_grid_within_bounds(
    voxel_grid: np.ndarray,
    origin: np.ndarray,
    bounds: AABB,
    voxel_size: float  
) -> np.ndarray:
    """
    Crops a dense occupancy voxel grid within true coordinate bounds.
    """

    crop_min = bounds.min_bound.numpy()
    crop_max = bounds.max_bound.numpy()

    min_idx = np.ceil((crop_min - origin) / voxel_size - 0.5).astype(int)
    max_idx = np.floor((crop_max - origin) / voxel_size - 0.5).astype(int) + 1

    grid_shape = np.array(voxel_grid.shape)
    min_idx = np.clip(min_idx, 0, grid_shape)
    max_idx = np.clip(max_idx, min_idx, grid_shape)

    cropped_grid = voxel_grid[
        min_idx[0]:max_idx[0],
        min_idx[1]:max_idx[1],
        min_idx[2]:max_idx[2]
    ]

    return cropped_grid.copy()


def estimate_cavity_volume_within_bounds(mesh: TriangleMesh, bounds: AABB, voxel_size: float) -> float:
    """
    Estimates the volume of a cavity in a mesh within the specified bounds using voxelization.
    """

    origin = mesh.get_axis_aligned_bounding_box().min_bound.numpy()

    voxel_grid = voxelize_mesh(mesh, voxel_size)    

    voxel_grid = crop_voxel_grid_within_bounds(voxel_grid, origin, bounds, voxel_size)
    voxel_coords = np.argwhere(voxel_grid != 0) * voxel_size + origin

    pcd = o3d.t.geometry.PointCloud(Tensor(voxel_coords, dtype=o3d.core.float32))
    hull = mesh_to_legacy(pcd.compute_convex_hull())

    hull_volume = hull.get_volume()
    solid_volume = np.sum(voxel_grid) * voxel_size**3

    return hull_volume - solid_volume
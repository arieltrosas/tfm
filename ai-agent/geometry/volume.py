import numpy as np
import open3d as o3d

from geometry.types import Tensor, AABB, TriangleMesh, mesh_to_tensor, mesh_to_legacy
from geometry.io import write_triangle_mesh, write_point_cloud
from geometry.voxelizer import voxelize_mesh


def extract_cavity_within_bounds(
    mesh: o3d.geometry.TriangleMesh, 
    bounds: AABB,
    voxel_size: float
) -> np.ndarray:
    """
    Extracts the cavity within specified bounds and returns an (N, 3) float array of real-world coordinates of empty cavity voxels.
    """

    origin = mesh.get_axis_aligned_bounding_box().min_bound.numpy()

    voxel_grid = voxelize_mesh(mesh, voxel_size)

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

    idx_out = np.argwhere(cropped_grid == 0)
    if len(idx_out) == 0:
        return np.empty((0, 3))

    cropped_origin = origin + (min_idx * voxel_size)
    half_voxel = voxel_size / 2.0
    roi_empty_coords = idx_out * voxel_size + cropped_origin + half_voxel

    hull_mesh, _ = mesh.compute_convex_hull()
    hull_tensor_mesh = o3d.t.geometry.TriangleMesh.from_legacy(hull_mesh)
    
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(hull_tensor_mesh)

    query_tensor = o3d.core.Tensor(roi_empty_coords, dtype=o3d.core.float32)
    occupancy = scene.compute_occupancy(query_tensor)
    
    is_cavity_mask = occupancy.numpy().astype(bool)
    cavity_coords = roi_empty_coords[is_cavity_mask]

    return cavity_coords
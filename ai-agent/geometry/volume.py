from pathlib import Path
from typing import Tuple, cast

import numpy as np
import open3d as o3d
from scipy import ndimage

from common.types import AABB


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

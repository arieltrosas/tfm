from geometry.types import Tensor, AABB, TriangleMesh, mesh_to_tensor, mesh_to_legacy
from geometry.voxel import voxelize_gpu, crop_voxel_grid

from geometry.io import write_triangle_mesh, write_point_cloud

import numpy as np
import open3d as o3d


def estimate_cavity_volume_within_bounds(mesh: TriangleMesh, bounds: AABB, voxel_size: float) -> float:

    origin = mesh.get_axis_aligned_bounding_box().min_bound.numpy()

    voxel_grid = voxelize_gpu(mesh, voxel_size)    

    voxel_grid = crop_voxel_grid(voxel_grid, origin, bounds, voxel_size)
    voxel_coords = np.argwhere(voxel_grid != 0) * voxel_size + origin

    pcd = o3d.t.geometry.PointCloud(Tensor(voxel_coords, dtype=o3d.core.float32))
    hull = mesh_to_legacy(pcd.compute_convex_hull())

    hull_volume = hull.get_volume()
    solid_volume = np.sum(voxel_grid) * voxel_size**3

    return hull_volume - solid_volume
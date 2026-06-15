from pathlib import Path

import numpy as np
import open3d as o3d

from common.types import AABB


def find_cavity_aabb(
    file_path: str,
    knn: int = 30,
    curvature_threshold: float = 0.05,
    eps: float = 0.05,
    min_points: int = 10,
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

    crack_pcd = pcd.select_by_index(crack_indices)  # pyright: ignore

    labels = np.array(crack_pcd.cluster_dbscan(eps=eps, min_points=min_points, print_progress=False))
    valid_labels = labels[labels >= 0]

    if len(valid_labels) == 0:
        return None

    largest_cluster_idx = np.argmax(np.bincount(valid_labels))
    final_crack_pcd = crack_pcd.select_by_index(np.where(labels == largest_cluster_idx)[0])  # pyright: ignore

    o3d_aabb = final_crack_pcd.get_axis_aligned_bounding_box()

    min_bound = np.array(o3d_aabb.get_min_bound())
    extent = np.array(o3d_aabb.get_extent())

    return AABB(
        x=float(min_bound[0]),
        y=float(min_bound[1]),
        z=float(min_bound[2]),
        w=float(extent[0]),
        h=float(extent[1]),
        d=float(extent[2]),
    )

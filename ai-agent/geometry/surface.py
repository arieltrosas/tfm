import numpy as np
import open3d as o3d

from geometry.types import Tensor, AABB, TriangleMesh, mesh_to_tensor, mesh_to_legacy
from geometry.io import write_triangle_mesh, write_point_cloud
from geometry.heat_method import compute_geodesic_distance


def estimate_surface_area(mesh: TriangleMesh, bounds: AABB) -> float:
    """
    Estimates the surface area of a mesh within the specified bounds.
    """

    mesh = mesh_to_legacy(mesh)
    mesh = mesh.crop(bounds)

    if mesh.is_empty():
        raise ValueError("Mesh geometry is empty")

    return mesh.get_surface_area()


def estimate_surface_distance(mesh: TriangleMesh, a: np.ndarray, b: np.ndarray) -> float:
    """
    Estimates the geodesic distance between two points on the surface of a mesh using the heat method.
    """

    mesh = mesh_to_legacy(mesh)

    if mesh.is_empty():
        raise ValueError("Mesh geometry is empty")

    if a.shape != b.shape:
        raise ValueError("Shape of a and b must be the same")

    if a.shape[0] != 3:
        raise ValueError("Shape of a must be (3,)")

    if b.shape[0] != 3:
        raise ValueError("Shape of b must be (3,)") 

    vertices = np.asarray(mesh.vertices, np.float64)
    triangles = np.asarray(mesh.triangles, np.int32)

    a_idx = np.argmin(np.linalg.norm(vertices - a, axis=1))
    b_idx = np.argmin(np.linalg.norm(vertices - b, axis=1))

    result = compute_geodesic_distance(vertices, triangles, [a_idx])
    distance = result.distance[b_idx]

    return distance
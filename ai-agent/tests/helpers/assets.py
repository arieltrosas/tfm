import open3d as o3d

from geometry.types import mesh_to_tensor, point_cloud_to_tensor


def make_sphere_mesh(radius: float = 1.0, resolution: int = 2) -> o3d.geometry.TriangleMesh:
    return o3d.geometry.TriangleMesh.create_sphere(radius=radius, resolution=resolution)


def make_point_cloud_from_mesh(
    mesh: o3d.geometry.TriangleMesh,
    num_points: int = 1000,
) -> o3d.geometry.PointCloud:
    return mesh.sample_points_uniformly(number_of_points=num_points)


def sphere_as_tensor_mesh(radius: float = 1.0, resolution: int = 2):
    return mesh_to_tensor(make_sphere_mesh(radius=radius, resolution=resolution))


def cloud_as_tensor_point_cloud(mesh: o3d.geometry.TriangleMesh, num_points: int = 1000):
    return point_cloud_to_tensor(make_point_cloud_from_mesh(mesh, num_points=num_points))

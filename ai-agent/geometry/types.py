import open3d as o3d

"""
Basic types.
"""

Tensor = o3d.core.Tensor
AABB = o3d.t.geometry.AxisAlignedBoundingBox

""""
Geometry types.
"""

TriangleMesh = o3d.t.geometry.TriangleMesh | o3d.geometry.TriangleMesh
PointCloud = o3d.t.geometry.PointCloud | o3d.geometry.PointCloud

def mesh_to_legacy(mesh: TriangleMesh) -> o3d.geometry.TriangleMesh:
    if isinstance(mesh, o3d.t.geometry.TriangleMesh):
        return mesh.to_legacy()
    return mesh


def mesh_to_tensor(mesh: TriangleMesh) -> o3d.t.geometry.TriangleMesh:
    if isinstance(mesh, o3d.geometry.TriangleMesh):
        return o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    return mesh


def point_cloud_to_legacy(point_cloud: PointCloud) -> o3d.geometry.PointCloud:
    if isinstance(point_cloud, o3d.t.geometry.PointCloud):
        return point_cloud.to_legacy()
    return point_cloud


def point_cloud_to_tensor(point_cloud: PointCloud) -> o3d.t.geometry.PointCloud:
    if isinstance(point_cloud, o3d.geometry.PointCloud):
        return o3d.t.geometry.PointCloud.from_legacy(point_cloud)
    return point_cloud
import numpy as np
import open3d as o3d

from geometry.types import TriangleMesh, mesh_to_tensor


def _validate_reduction(reduction: float) -> None:
    if not np.isfinite(reduction):
        raise ValueError("reduction must be a finite number")
    if reduction < 0.0 or reduction >= 1.0:
        raise ValueError("reduction must be in the range [0.0, 1.0)")


def _has_vertex_colors(mesh: o3d.t.geometry.TriangleMesh) -> bool:
    return "colors" in mesh.vertex


def _has_texture_uvs(mesh: o3d.t.geometry.TriangleMesh) -> bool:
    return "texture_uvs" in mesh.triangle


def _create_raycasting_scene(
    source_mesh: o3d.t.geometry.TriangleMesh,
) -> o3d.t.geometry.RaycastingScene:
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(source_mesh.cpu())
    return scene


def _transfer_vertex_colors(
    source_mesh: o3d.t.geometry.TriangleMesh,
    target_mesh: o3d.t.geometry.TriangleMesh,
    scene: o3d.t.geometry.RaycastingScene | None = None,
) -> None:
    """
    Project each target vertex onto the source surface and interpolate
    triangle colors with barycentric coordinates.
    """
    if not _has_vertex_colors(source_mesh):
        return
    if target_mesh.vertex.positions.shape[0] == 0:
        return

    if scene is None:
        scene = _create_raycasting_scene(source_mesh)

    source_triangles = source_mesh.triangle.indices.cpu().numpy()
    source_colors = source_mesh.vertex.colors.cpu().numpy()
    target_positions = target_mesh.vertex.positions.cpu()

    result = scene.compute_closest_points(target_positions)
    primitive_ids = result["primitive_ids"].numpy()
    barycentric = result["primitive_uvs"].numpy()
    valid = primitive_ids >= 0

    target_colors = np.zeros(
        (target_positions.shape[0], source_colors.shape[1]),
        dtype=source_colors.dtype,
    )

    if np.any(valid):
        triangle_ids = primitive_ids[valid]
        bary = barycentric[valid]
        source_triangle_vertices = source_triangles[triangle_ids]

        c0 = source_colors[source_triangle_vertices[:, 0]]
        c1 = source_colors[source_triangle_vertices[:, 1]]
        c2 = source_colors[source_triangle_vertices[:, 2]]

        # Open3D returns barycentric coords for the 2nd and 3rd vertices.
        w0 = 1.0 - bary[:, 0] - bary[:, 1]
        w1 = bary[:, 0]
        w2 = bary[:, 1]

        target_colors[valid] = (
            c0 * w0[:, None] + c1 * w1[:, None] + c2 * w2[:, None]
        )

    target_mesh.vertex.colors = o3d.core.Tensor(
        target_colors,
        dtype=source_mesh.vertex.colors.dtype,
        device=target_mesh.vertex.positions.device,
    )


def _transfer_texture_uvs(
    source_mesh: o3d.t.geometry.TriangleMesh,
    target_mesh: o3d.t.geometry.TriangleMesh,
    scene: o3d.t.geometry.RaycastingScene | None = None,
) -> None:
    """
    Transfer per-triangle-corner UVs so seams are preserved.
    Each target triangle corner is projected independently.
    """
    if not _has_texture_uvs(source_mesh):
        return
    if target_mesh.triangle.indices.shape[0] == 0:
        return

    if scene is None:
        scene = _create_raycasting_scene(source_mesh)

    source_uvs = source_mesh.triangle.texture_uvs.cpu().numpy()
    target_triangles = target_mesh.triangle.indices.cpu().numpy()
    target_positions = target_mesh.vertex.positions.cpu().numpy()

    source_triangle_count = source_mesh.triangle.indices.shape[0]
    if source_uvs.shape[0] != source_triangle_count * 3:
        raise ValueError(
            "Source mesh contains malformed texture_uvs: "
            f"expected {source_triangle_count * 3} UVs, "
            f"got {source_uvs.shape[0]}"
        )

    corner_vertex_indices = target_triangles.reshape(-1)
    corner_positions = target_positions[corner_vertex_indices]

    query = o3d.core.Tensor(
        corner_positions,
        dtype=o3d.core.Dtype.Float32,
        device=o3d.core.Device("CPU:0"),
    )
    result = scene.compute_closest_points(query)
    primitive_ids = result["primitive_ids"].numpy()
    barycentric = result["primitive_uvs"].numpy()

    target_uvs = np.zeros(
        (corner_positions.shape[0], 2),
        dtype=source_uvs.dtype,
    )
    valid = primitive_ids >= 0

    if np.any(valid):
        source_uv_triangles = source_uvs.reshape(-1, 3, 2)
        source_triangle_uvs = source_uv_triangles[primitive_ids[valid]]
        bary = barycentric[valid]

        uv0 = source_triangle_uvs[:, 0]
        uv1 = source_triangle_uvs[:, 1]
        uv2 = source_triangle_uvs[:, 2]

        w0 = 1.0 - bary[:, 0] - bary[:, 1]
        w1 = bary[:, 0]
        w2 = bary[:, 1]

        target_uvs[valid] = (
            uv0 * w0[:, None] + uv1 * w1[:, None] + uv2 * w2[:, None]
        )

    target_mesh.triangle.texture_uvs = o3d.core.Tensor(
        target_uvs,
        dtype=source_mesh.triangle.texture_uvs.dtype,
        device=target_mesh.triangle.indices.device,
    )


def _transfer_appearance(
    source_mesh: o3d.t.geometry.TriangleMesh,
    target_mesh: o3d.t.geometry.TriangleMesh,
) -> None:
    needs_surface_projection = (
        _has_vertex_colors(source_mesh) or _has_texture_uvs(source_mesh)
    )
    scene = (
        _create_raycasting_scene(source_mesh)
        if needs_surface_projection
        else None
    )

    if _has_vertex_colors(source_mesh):
        _transfer_vertex_colors(source_mesh, target_mesh, scene)

    if _has_texture_uvs(source_mesh):
        _transfer_texture_uvs(source_mesh, target_mesh, scene)

    target_mesh.material = o3d.visualization.Material(source_mesh.material)


def simplify_mesh(
    mesh: TriangleMesh,
    reduction: float = 0.5,
) -> o3d.t.geometry.TriangleMesh:
    """
    Simplify a mesh with quadric decimation while preserving appearance
    attributes (vertex colors, texture UVs, material) when present.
    """
    _validate_reduction(reduction)

    source_mesh = mesh_to_tensor(mesh)

    if source_mesh.is_empty():
        raise ValueError("Input mesh is empty")

    source_triangle_count = source_mesh.triangle.indices.shape[0]
    if source_triangle_count == 0:
        raise ValueError("Input mesh contains no triangles")

    simplified_mesh = source_mesh.simplify_quadric_decimation(
        target_reduction=reduction
    )
    _transfer_appearance(source_mesh, simplified_mesh)
    simplified_mesh.compute_vertex_normals()

    return simplified_mesh

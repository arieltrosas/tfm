from pathlib import Path

from mcp.server.fastmcp import FastMCP

import numpy as np
import open3d as o3d

from typing import Literal

from geometry.types import (
    mesh_to_legacy,
    mesh_to_tensor,
    point_cloud_to_legacy,
    point_cloud_to_tensor,
)

from geometry.io import (
    is_supported_point_cloud_format,
    is_supported_triangle_mesh_format,
    read_triangle_mesh,
    read_point_cloud,
    write_triangle_mesh,
    write_point_cloud,
)
from geometry.simplify import simplify_mesh as simplify_mesh_geometry

from common.types import AABB

from ...types import GeometryInfoResult, aabb_from_o3d, aabb_to_o3d
from ...common import resolve_within_root
from ...api_client import workspace


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_geometry_info(filename: str) -> GeometryInfoResult:
        """
        Read basic geometry information about a file in the workspace.
        This includes format, vertex/point count, face count, bounding box, etc...
        """

        root = Path(await workspace())
        path = resolve_within_root(root, filename)

        result = GeometryInfoResult()
        
        if is_supported_triangle_mesh_format(path):
            mesh = mesh_to_legacy(read_triangle_mesh(path))
            result.type = "mesh"
            result.vertex_count = len(mesh.vertices)
            result.face_count = len(mesh.triangles)
            result.bounds = aabb_from_o3d(mesh.get_axis_aligned_bounding_box())
        elif is_supported_point_cloud_format(path):
            point_cloud = point_cloud_to_legacy(read_point_cloud(path))
            result.type = "point_cloud"
            result.point_count = len(point_cloud.points)
            result.bounds = aabb_from_o3d(point_cloud.get_axis_aligned_bounding_box())
        else:
            raise ValueError(f"File is not a valid geometry file: {path}")
        
        return result


    @mcp.tool()
    async def convert_mesh_format(input_file: str, output_file: str) -> str:
        """
        Convert a mesh file in the workspace to another supported mesh format based on file extension.
        Reads from input_file and writes the result to output_file.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        write_triangle_mesh(output_path, read_triangle_mesh(input_path))

        return output_path.name
        

    @mcp.tool()
    async def convert_point_cloud_format(input_file: str, output_file: str) -> str:
        """
        Convert a point cloud file in the workspace to another supported point cloud format.
        Reads from input_file and writes the result to output_file.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        write_point_cloud(output_path, read_point_cloud(input_path))
        
        return output_path.name


    @mcp.tool()
    async def simplify_mesh(
        input_file: str,
        output_file: str,
        reduction: float=0.5,
    ) -> str:
        """
        Simplify a mesh and write the result to a file in the workspace.
        Preserves appearance attributes (vertex colors, texture UVs, material)
        when present on the input mesh.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)

        mesh = simplify_mesh_geometry(read_triangle_mesh(input_path), reduction)
        write_triangle_mesh(output_path, mesh)

        return output_path.name


    @mcp.tool()
    async def downsample_point_cloud(
        input_file: str,
        output_file: str,
        voxel_size: float,
    ) -> str:
        """
        Downsamples a point cloud using voxel grid filtering and write the result to a file.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        point_cloud = point_cloud_to_tensor(read_point_cloud(input_path))
        point_cloud = point_cloud.voxel_down_sample(voxel_size=voxel_size)
        write_point_cloud(output_path, point_cloud)

        return output_path.name


    @mcp.tool()
    async def transform_mesh(
        input_file: str,
        output_file: str,
        translate: list[float] | None = None,
        rotate: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> str:
        """
        Apply translate, rotate, and/or scale transforms to a mesh and write the result to a file.
        Angles are given in degrees.
        Scale is applied to the mesh respect to the coordinate origin.
        Rotation is performed around the coordinate origin.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        mesh = mesh_to_tensor(read_triangle_mesh(input_path))

        T = np.eye(4, dtype=np.float32)

        if scale is not None:
            T[:3, :3] = np.diag(scale)

        if rotate is not None:
            rotate = np.asarray(rotate) * np.pi / 180.0
            R = o3d.geometry.get_rotation_matrix_from_xyz(rotate)
            T[:3, :3] = R @ T[:3, :3]

        if translate is not None:
            T[:3, 3] = translate

        mesh = mesh.transform(o3d.core.Tensor(T))
        write_triangle_mesh(output_path, mesh)

        return output_path.name


    @mcp.tool()
    async def transform_point_cloud(
        input_file: str,
        output_file: str,
        translate: list[float] | None = None,
        rotate: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> str:
        """
        Apply translate, rotate, and/or scale transforms to a point cloud and write the result to a file.
        Angles are given in degrees.
        Scale is applied to the point cloud respect to the coordinate origin.
        Rotation is performed around the coordinate origin.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        point_cloud = point_cloud_to_tensor(read_point_cloud(input_path))

        T = np.eye(4, dtype=np.float32)

        if scale is not None:
            T[:3, :3] = np.diag(scale)

        if rotate is not None:
            rotate = np.asarray(rotate) * np.pi / 180.0
            R = o3d.geometry.get_rotation_matrix_from_xyz(rotate)
            T[:3, :3] = R @ T[:3, :3]

        if translate is not None:
            T[:3, 3] = translate

        point_cloud = point_cloud.transform(o3d.core.Tensor(T))
        write_point_cloud(output_path, point_cloud)

        return output_path.name


    @mcp.tool()
    async def sample_mesh_surface(
        input_file: str,
        output_file: str,
        num_points: int = 100_000,
    ) -> str:
        """
        Sample a mesh surface uniformly and write the result as a point cloud file.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        mesh = mesh_to_tensor(read_triangle_mesh(input_path))
        point_cloud = mesh.sample_points_uniformly(number_of_points=num_points)
        write_point_cloud(output_path, point_cloud)

        return output_path.name


    @mcp.tool()
    async def reconstruct_mesh_from_point_cloud(
        input_file: str,
        output_file: str,
        depth: int = 9,
    ) -> str:
        """
        Reconstruct a mesh from a point cloud using Poisson surface reconstruction.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        point_cloud = point_cloud_to_legacy(read_point_cloud(input_path))
        point_cloud.estimate_normals()
        mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            point_cloud,
            depth=depth,
        )
        write_triangle_mesh(output_path, mesh)

        return output_path.name


    @mcp.tool()
    async def crop_mesh(
        input_file: str,
        output_file: str,
        aabb: AABB,
    ) -> str:
        """
        Crop a mesh to a given bounding box and write the result to a file.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))
        mesh = mesh.crop(aabb_to_o3d(aabb).to_legacy())
        write_triangle_mesh(output_path, mesh)

        return output_path.name

    
    @mcp.tool()
    async def mesh_is_watertight(
        input_file: str
    ) -> bool:
        """
        Check if a mesh is watertight.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        return mesh.is_watertight()
    

    @mcp.tool()
    async def mesh_is_manifold(
        input_file: str
    ) -> bool:
        """
        Check if a mesh is manifold.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        is_vertex_manifold = mesh.is_vertex_manifold()
        is_edge_manifold = mesh.is_edge_manifold()

        return is_vertex_manifold and is_edge_manifold
    

    @mcp.tool()
    async def mesh_is_orientable(
        input_file: str
    ) -> bool:
        """
        Check if a mesh is orientable.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        return mesh.is_orientable()
    

    @mcp.tool()
    async def mesh_is_self_intersecting(
        input_file: str
    ) -> bool:
        """
        Check if a mesh is self-intersecting.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        return mesh.is_self_intersecting()
    
    
    @mcp.tool()
    async def mesh_cleanup(
        input_file: str,
        output_file: str,
        clean: list[Literal["vertices", "triangles", "edges"]] = ["vertices", "triangles", "edges"],
    ) -> str:
        """
        Clean a mesh by removing unreferenced vertices, degenerate triangles, duplicated triangles, duplicated vertices, and non-manifold edges.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        if "vertices" in clean:
            mesh = mesh.remove_unreferenced_vertices()
            mesh = mesh.remove_duplicated_vertices()
        if "triangles" in clean:
            mesh = mesh.remove_degenerate_triangles()
            mesh = mesh.remove_duplicated_triangles()
        if "edges" in clean:
            mesh = mesh.remove_non_manifold_edges()

        write_triangle_mesh(output_path, mesh)

        return output_path.name


    @mcp.tool()
    async def mesh_compute_vertex_normals(
        input_file: str,
        output_file: str,
    ) -> str:
        """
        Compute vertex normals for a mesh.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        mesh = mesh.compute_vertex_normals()
        write_triangle_mesh(output_path, mesh)

        return output_path.name
    

    @mcp.tool()
    async def mesh_compute_triangle_normals(
        input_file: str,
        output_file: str,
    ) -> str:
        """
        Compute triangle normals for a mesh.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        mesh = mesh.compute_triangle_normals()
        write_triangle_mesh(output_path, mesh)

        return output_path.name


    @mcp.tool()
    async def mesh_filter_average(
        input_file: str,
        output_file: str,
        iterations: int = 1,
    ) -> str:
        """
        Smooth a mesh using average filtering.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        mesh = mesh.filter_smooth_simple(number_of_iterations=iterations)
        write_triangle_mesh(output_path, mesh)

        return output_path.name


    @mcp.tool()
    async def mesh_filter_taubin(
        input_file: str,
        output_file: str,
        iterations: int = 1,
    ) -> str:
        """
        Smooth a mesh using Taubin filtering.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        mesh = mesh.filter_smooth_taubin(number_of_iterations=iterations)
        write_triangle_mesh(output_path, mesh)

        return output_path.name
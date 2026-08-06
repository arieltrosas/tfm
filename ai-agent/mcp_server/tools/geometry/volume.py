from pathlib import Path

from mcp.server.fastmcp import FastMCP

import numpy as np
import open3d as o3d

from common.types import AABB

from ...common import resolve_within_root
from ...api_client import workspace
from ...types import aabb_from_o3d, aabb_to_o3d

from geometry.io import read_triangle_mesh, write_point_cloud, write_triangle_mesh
from geometry.types import AABB as O3DAABB, mesh_to_legacy
from geometry.volume import extract_cavity_within_bounds
from geometry.curvature import cluster_cavities


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def compute_volume(input_file: str) -> float:
        """
        Compute the volume of a mesh.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        return mesh.get_volume()


    @mcp.tool()
    async def extract_cavity(
        input_file: str,
        output_file: str,
        aabb: AABB,
        voxel_size: float,
    ) -> str:
        """
        Extract cavity voxel coordinates within a region and write it to a file as a mesh.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        output_path = resolve_within_root(root, output_file)

        mesh = mesh_to_legacy(read_triangle_mesh(input_path))
        cavity_coords = extract_cavity_within_bounds(mesh, aabb_to_o3d(aabb), voxel_size)

        cavity_cloud = o3d.geometry.PointCloud()
        if len(cavity_coords) > 0:
            cavity_cloud.points = o3d.utility.Vector3dVector(cavity_coords)

        write_point_cloud(output_path, cavity_cloud)

        return output_path.name
        

    @mcp.tool()
    async def detect_cavities(
        input_file: str,
        percentile: float = 5.0,
        min_points: int = 5,
    ) -> list[AABB]:
        """
        Detect negatively curved (cavity-like) regions on a mesh using mean curvature clustering.
        Returns a list of bounding boxes for each detected cavity.
        """

        root = Path(await workspace())
        input_path = resolve_within_root(root, input_file)
        mesh = mesh_to_legacy(read_triangle_mesh(input_path))

        clusters = cluster_cavities(mesh, percentile, min_points)
        vertices = np.asarray(mesh.vertices)

        cavities = []
        for cluster in clusters:
            cluster_vertices = vertices[cluster]
            min_bound = np.min(cluster_vertices, axis=0)
            max_bound = np.max(cluster_vertices, axis=0)
            cavities.append(aabb_from_o3d(O3DAABB(min_bound=min_bound, max_bound=max_bound)))

        return cavities

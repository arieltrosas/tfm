from mcp.server.fastmcp import FastMCP

import numpy as np

from common.types import AABB

from ...common import resolve_within_root
from ...types import aabb_from_o3d

from geometry.io import read_triangle_mesh, write_triangle_mesh
from geometry.types import mesh_to_legacy
from geometry.volume import extract_cavity_within_bounds
from geometry.curvature import cluster_cavities


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def compute_volume(input_file: str) -> float:
        """
        Compute the volume of a mesh.
        """

        input_path = await resolve_within_root(input_file)
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

        input_path = await resolve_within_root(input_file)
        output_path = await resolve_within_root(output_file)

        mesh = read_triangle_mesh(input_path)
        cavity = extract_cavity_within_bounds(mesh, aabb, voxel_size)

        write_triangle_mesh(output_path, cavity)

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

        input_path = await resolve_within_root(input_file)
        mesh = read_triangle_mesh(input_path)

        clusters = cluster_cavities(mesh, percentile, min_points)
        vertices = np.asarray(mesh.vertices)

        cavities = []
        for cluster in clusters:
            cluster_vertices = vertices[cluster]
            min_bound = np.min(cluster_vertices, axis=0)
            max_bound = np.max(cluster_vertices, axis=0)
            cavities.append(aabb_from_o3d(min_bound, max_bound))

        return cavities

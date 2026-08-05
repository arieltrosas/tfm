from mcp.server.fastmcp import FastMCP

import numpy as np

from geometry.io import read_triangle_mesh
from geometry.surface import estimate_surface_area, estimate_surface_distance

from common.types import AABB

from ...types import aabb_to_o3d
from ...common import resolve_within_root

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def measure_surface_distance(
        input_file: str,
        a: list[float],
        b: list[float],
    ) -> float:
        """
        Measure the geodesic surface distance between two points on a mesh using the heat method.
        """
        input_path = await resolve_within_root(input_file)
        mesh = read_triangle_mesh(input_path)
        a, b = np.array(a), np.array(b)
        return estimate_surface_distance(mesh, a, b)

    
    @mcp.tool()
    async def measure_surface_area(
        input_file: str,
        bounds: AABB
    ) -> float:
        """
        Measure the surface area of the mesh within the specified bounds.
        """
        input_path = await resolve_within_root(input_file)
        mesh = read_triangle_mesh(input_path)
        return estimate_surface_distance(mesh, aabb_to_o3d(bounds))
        


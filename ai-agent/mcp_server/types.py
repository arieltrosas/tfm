from typing import Literal

import open3d as o3d
from pydantic import BaseModel, Field

from geometry.types import AABB as O3DAABB
from common.types import AABB


def aabb_to_o3d(aabb: AABB) -> O3DAABB:
    return O3DAABB(
        min_bound=[aabb.x, aabb.y, aabb.z],
        max_bound=[aabb.x + aabb.w, aabb.y + aabb.h, aabb.z + aabb.d],
    )


def aabb_from_o3d(aabb: O3DAABB) -> AABB:
    min_bound = aabb.min_bound.numpy()
    max_bound = aabb.max_bound.numpy()
    size = max_bound - min_bound
    return AABB(
        x=float(min_bound[0]),
        y=float(min_bound[1]),
        z=float(min_bound[2]),
        w=float(size[0]),
        h=float(size[1]),
        d=float(size[2]),
    )


class ToolResult(BaseModel):
    status: Literal["success", "error"] = "success"
    error: str | None = None


class GeometryInfoResult(ToolResult):
    type: Literal["mesh", "point_cloud", "unknown"] = "unknown"
    vertex_count: int | None = None
    point_count: int | None = None
    face_count: int | None = None
    bounds: AABB | None = None
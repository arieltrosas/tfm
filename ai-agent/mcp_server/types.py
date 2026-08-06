from typing import Literal

import numpy as np
import open3d as o3d
from pydantic import BaseModel, Field

from geometry.types import AABB as O3DAABB
from common.types import AABB


def _bound_to_numpy(bound) -> np.ndarray:
    if hasattr(bound, "numpy"):
        return bound.numpy()
    return np.asarray(bound)


def aabb_to_o3d(aabb: AABB) -> O3DAABB:
    return O3DAABB(
        min_bound=[aabb.x, aabb.y, aabb.z],
        max_bound=[aabb.x + aabb.w, aabb.y + aabb.h, aabb.z + aabb.d],
    )


def aabb_from_o3d(aabb: O3DAABB) -> AABB:
    min_bound = _bound_to_numpy(aabb.min_bound)
    max_bound = _bound_to_numpy(aabb.max_bound)
    size = max_bound - min_bound
    return AABB(
        x=float(min_bound[0]),
        y=float(min_bound[1]),
        z=float(min_bound[2]),
        w=float(size[0]),
        h=float(size[1]),
        d=float(size[2]),
    )


class GeometryInfoResult(BaseModel):
    type: Literal["mesh", "point_cloud", "unknown"] = "unknown"
    vertex_count: int | None = None
    point_count: int | None = None
    face_count: int | None = None
    bounds: AABB | None = None
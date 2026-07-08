"""
Voxelize a mesh using `geometry.voxel.Renderer`, then:
1) Build and visualize a voxel point cloud with Open3D.
2) Show a matplotlib slideshow of color/stencil slices.
"""

from _bootstrap import setup

setup()

import matplotlib.pyplot as plt
import numpy as np
import open3d as o3d
from matplotlib.widgets import Slider

from geometry.types import TriangleMesh, mesh_to_tensor
from geometry.io import read_triangle_mesh
from geometry.voxel import Renderer


def voxelize_with_renderer(
    mesh: TriangleMesh,
    voxel_size: float,
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[np.ndarray], list[float]]:
    """
    Voxelize a mesh and return:
    - voxel occupancy grid (z, y, x)
    - minimum world bound
    - stencil slices
    - color slices
    """
    
    mesh = mesh_to_tensor(mesh)

    if mesh.is_empty():
        raise ValueError("Mesh is empty")

    min_bound = mesh.get_axis_aligned_bounding_box().min_bound.numpy()
    max_bound = mesh.get_axis_aligned_bounding_box().max_bound.numpy()
    extent = max_bound - min_bound

    width = int(extent[0] / voxel_size) + 1
    height = int(extent[1] / voxel_size) + 1
    nslices = int(extent[2] / voxel_size) + 1

    renderer = Renderer(render_color=True)
    renderer.initialize(width, height)
    renderer.upload_model(
        min_bound,
        max_bound,
        mesh.vertex.positions.numpy(),
        mesh.triangle.indices.numpy(),
    )

    stencil_slices: list[np.ndarray] = []
    color_slices: list[np.ndarray] = []
    slice_depths: list[float] = []

    renderer.render_begin()
    try:
        for i in range(nslices + 1):
            depth = max_bound[2] - i * voxel_size
            stencil, color = renderer.render_slice(depth)
            stencil_slices.append(stencil.copy())
            color_slices.append(color.copy() if color is not None else np.zeros((height, width, 4), dtype=np.uint8))
            slice_depths.append(float(depth))
    finally:
        renderer.render_end()
        renderer.destroy()

    stencil_slices.reverse()
    color_slices.reverse()
    slice_depths.reverse()

    voxel_grid = np.stack(stencil_slices, axis=0)
    occupancy = np.where(voxel_grid != 0, 1, 0).astype(np.uint8)
    return occupancy, min_bound, stencil_slices, color_slices, slice_depths


def build_voxel_point_cloud(
    occupancy: np.ndarray,
    min_bound: np.ndarray,
    voxel_size: float,
) -> o3d.t.geometry.PointCloud:
    voxel_indices = np.argwhere(occupancy != 0)[:, [2, 1, 0]]
    voxel_coords = (voxel_indices + 0.5) * voxel_size + min_bound
    return o3d.t.geometry.PointCloud(o3d.core.Tensor(voxel_coords, dtype=o3d.core.float32))


def show_slice_slideshow(
    color_slices: list[np.ndarray],
    stencil_slices: list[np.ndarray],
    slice_depths: list[float],
) -> None:
    if not stencil_slices:
        raise ValueError("No slices to display")
    if len(slice_depths) != len(stencil_slices):
        raise ValueError("`slice_depths` length must match number of slices")

    total = len(stencil_slices)
    start_idx = 0

    fig, (ax_color, ax_stencil) = plt.subplots(1, 2, figsize=(12, 5))
    plt.subplots_adjust(bottom=0.2)

    color_img = ax_color.imshow(np.flipud(color_slices[start_idx]))
    ax_color.set_title(f"Color depth z={slice_depths[start_idx]:.6f}")
    ax_color.axis("off")

    stencil_img = ax_stencil.imshow(
        np.flipud(stencil_slices[start_idx]),
        cmap="gray",
        vmin=0,
        vmax=255,
    )
    ax_stencil.set_title(f"Stencil depth z={slice_depths[start_idx]:.6f}")
    ax_stencil.axis("off")

    slider_ax = fig.add_axes((0.15, 0.07, 0.7, 0.04))
    slider = Slider(
        ax=slider_ax,
        label="Slice",
        valmin=0,
        valmax=total - 1,
        valinit=start_idx,
        valstep=1,
    )
    tick_positions = np.linspace(0, total - 1, num=min(7, total), dtype=int)
    tick_positions = np.unique(tick_positions)
    slider_ax.set_xticks(tick_positions)
    slider_ax.set_xticklabels([f"{slice_depths[idx]:.4f}" for idx in tick_positions])
    slider_ax.set_xlabel("Depth (z)")

    def update(index: float) -> None:
        idx = int(index)
        color_img.set_data(np.flipud(color_slices[idx]))
        stencil_img.set_data(np.flipud(stencil_slices[idx]))
        ax_color.set_title(f"Color depth z={slice_depths[idx]:.6f}")
        ax_stencil.set_title(f"Stencil depth z={slice_depths[idx]:.6f}")
        fig.canvas.draw_idle()

    slider.on_changed(update)
    plt.show()


def main() -> None:
    mesh: TriangleMesh = read_triangle_mesh(o3d.data.KnotMesh().path)
    voxel_size: float = mesh.get_axis_aligned_bounding_box().get_extent().max().numpy() / 100.0

    if voxel_size <= 0:
        raise ValueError("`voxel_size` must be > 0.")

    occupancy, min_bound, stencil_slices, color_slices, slice_depths = voxelize_with_renderer(mesh, voxel_size)
    volume = float(np.sum(occupancy != 0) * (voxel_size ** 3))
    print(f"Voxelized volume: {volume}")

    point_cloud = build_voxel_point_cloud(occupancy, min_bound, voxel_size)
    o3d.visualization.draw([{"name": "voxel_point_cloud", "geometry": point_cloud}], show_ui=True)

    show_slice_slideshow(color_slices, stencil_slices, slice_depths)


if __name__ == "__main__":
    main()

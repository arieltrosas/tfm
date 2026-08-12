from pathlib import Path

from geometry.io import (
    is_supported_point_cloud_format,
    is_supported_triangle_mesh_format,
    is_supported_triangle_mesh_format,
    read_triangle_mesh,
    write_triangle_mesh,
)


class GeometryService:

    def __init__(self) -> None:
        pass

    def is_supported_mesh_file(self, file_path: str) -> bool:
        return is_supported_triangle_mesh_format(file_path)

    def is_supported_point_cloud_file(self, file_path: str) -> bool:
        return is_supported_point_cloud_format(file_path)

    def convert_mesh(self, src_path: str, dst_path: str) -> None:
        src_path = Path(src_path)
        dst_path = Path(dst_path)

        if not src_path.exists():
            raise FileNotFoundError(f"File '{src_path}' not found")
        if not src_path.is_file():
            raise IsADirectoryError(f"File '{src_path}' is a directory")
        if not dst_path.parent.exists():
            raise FileNotFoundError(f"Directory '{dst_path.parent}' not found")
        if not dst_path.parent.is_dir():
            raise IsADirectoryError(f"Directory '{dst_path.parent}' is not a directory")
        if not is_supported_triangle_mesh_format(src_path):
            raise ValueError(f"File '{src_path}' is not a valid mesh format")
        if not is_supported_triangle_mesh_format(dst_path):
            raise ValueError(f"File '{dst_path}' is not a valid mesh format")

        mesh = read_triangle_mesh(src_path)
        write_triangle_mesh(dst_path, mesh)

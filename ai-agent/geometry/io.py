import open3d as o3d
from pathlib import Path

SUPPORTED_POINT_CLOUD_FORMATS = [".xyz", ".xyzn", ".xyzrgb", ".xyzrgba", ".pts", ".pcd"]
SUPPORTED_TRIANGLE_MESH_FORMATS = [".ply", ".stl", ".obj", ".off", ".gltf", ".glb"]

def is_supported_point_cloud_format(file_path: str | Path) -> bool:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File '{file_path}' not found")
    if not file_path.is_file():
        raise IsADirectoryError(f"File '{file_path}' is a directory")
    return file_path.suffix.lower() in SUPPORTED_POINT_CLOUD_FORMATS

def is_supported_triangle_mesh_format(file_path: str | Path) -> bool:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File '{file_path}' not found")
    if not file_path.is_file():
        raise IsADirectoryError(f"File '{file_path}' is a directory")
    return is_supported_triangle_mesh_extension(file_path)


def is_supported_triangle_mesh_extension(file_path: str | Path) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_TRIANGLE_MESH_FORMATS

def read_point_cloud(file_path: str | Path) -> o3d.geometry.PointCloud:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File '{file_path}' not found")
    if not file_path.is_file():
        raise IsADirectoryError(f"File '{file_path}' is a directory")
    
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        raise ValueError(f"File '{file_path}' is not a valid point cloud")
    return pcd  

def read_triangle_mesh(file_path: str | Path) -> o3d.geometry.TriangleMesh:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File '{file_path}' not found")
    if not file_path.is_file():
        raise IsADirectoryError(f"File '{file_path}' is a directory")
    mesh = o3d.io.read_triangle_mesh(file_path)
    if not mesh:
        raise ValueError(f"File '{file_path}' is not a valid triangle mesh")
    return mesh

def write_point_cloud(file_path: str, point_cloud: o3d.geometry.PointCloud) -> None:
    file_path = Path(file_path)
    if not file_path.parent.exists():
        raise FileNotFoundError(f"Directory '{file_path.parent}' not found")
    if not file_path.parent.is_dir():
        raise IsADirectoryError(f"Directory '{file_path.parent}' is not a directory")
    o3d.io.write_point_cloud(file_path, point_cloud)

def write_triangle_mesh(file_path: str, triangle_mesh: o3d.geometry.TriangleMesh) -> None:
    file_path = Path(file_path)
    if not file_path.parent.exists():
        raise FileNotFoundError(f"Directory '{file_path.parent}' not found")
    if not file_path.parent.is_dir():
        raise IsADirectoryError(f"Directory '{file_path.parent}' is not a directory")
    o3d.io.write_triangle_mesh(file_path, triangle_mesh)

def convert_point_cloud_to_pcd(input_path: str | Path, output_path: str | Path | None = None) -> None:
    pcd = read_point_cloud(input_path)

    if output_path is None:
        output_path = input_path.with_suffix(".pcd")
    if not output_path.suffix == ".pcd":
        output_path = output_path.with_suffix(".pcd")
    
    write_point_cloud(output_path, pcd)

def convert_triangle_mesh_to_glb(input_path: str | Path, output_path: str | Path | None = None) -> None:
    mesh = read_triangle_mesh(input_path)

    if output_path is None:
        output_path = input_path.with_suffix(".glb")
    if not output_path.suffix == ".glb":
        output_path = output_path.with_suffix(".glb")
    
    write_triangle_mesh(output_path, mesh)

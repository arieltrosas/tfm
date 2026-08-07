from pathlib import Path

import httpx
import open3d as o3d
import pytest
from mcp import ClientSession

from geometry.io import read_triangle_mesh
from tests.helpers.mcp import call_tool, parse_tool_result

EXPECTED_TOOL_NAMES = {
    "get_app_state",
    "list_workspace_files",
    "write_file",
    "read_file",
    "delete_file",
    "get_geometry_info",
    "convert_mesh_format",
    "convert_point_cloud_format",
    "simplify_mesh",
    "downsample_point_cloud",
    "transform_mesh",
    "transform_point_cloud",
    "sample_mesh_surface",
    "reconstruct_mesh_from_point_cloud",
    "crop_mesh",
    "mesh_is_watertight",
    "mesh_is_manifold",
    "mesh_is_orientable",
    "mesh_is_self_intersecting",
    "mesh_cleanup",
    "mesh_compute_normals",
    "mesh_filter_average",
    "mesh_filter_taubin",
    "compute_volume",
    "extract_cavity",
    "detect_cavities",
    "measure_surface_distance",
    "measure_surface_area",
}


@pytest.mark.asyncio
async def test_all_tools_registered(mcp_session: ClientSession) -> None:
    tools = await mcp_session.list_tools()
    tool_names = {tool.name for tool in tools.tools}
    assert tool_names == EXPECTED_TOOL_NAMES


@pytest.mark.asyncio
async def test_mcp_tools_workflow(
    api_server: str,
    mcp_session: ClientSession,
    seed_workspace: dict[str, str],
) -> None:
    mesh_file = seed_workspace["mesh"]
    cloud_file = seed_workspace["cloud"]

    # Workspace / state
    report_content = "integration test report"
    report_name = parse_tool_result(
        await call_tool(
            mcp_session,
            "write_file",
            {"filename": "report.txt", "content": report_content},
        )
    )
    assert report_name == "report.txt"

    files = parse_tool_result(await call_tool(mcp_session, "list_workspace_files"))
    assert report_name in files
    assert mesh_file in files
    assert cloud_file in files

    read_content = parse_tool_result(
        await call_tool(mcp_session, "read_file", {"filename": report_name})
    )
    assert read_content == report_content

    deleted = parse_tool_result(
        await call_tool(mcp_session, "delete_file", {"files": [report_name]})
    )
    assert report_name in deleted

    files_after_delete = parse_tool_result(
        await call_tool(mcp_session, "list_workspace_files")
    )
    assert report_name not in files_after_delete

    app_state = parse_tool_result(await call_tool(mcp_session, "get_app_state"))
    assert app_state["workspace_dir"]
    assert len(app_state["files"]) >= 2

    # Mesh info & conversion
    mesh_info = parse_tool_result(
        await call_tool(mcp_session, "get_geometry_info", {"filename": mesh_file})
    )
    assert mesh_info["type"] == "mesh"
    assert mesh_info["vertex_count"] > 0
    assert mesh_info["face_count"] > 0
    assert mesh_info["bounds"] is not None

    cloud_info = parse_tool_result(
        await call_tool(mcp_session, "get_geometry_info", {"filename": cloud_file})
    )
    assert cloud_info["type"] == "point_cloud"
    assert cloud_info["point_count"] > 0

    obj_name = parse_tool_result(
        await call_tool(
            mcp_session,
            "convert_mesh_format",
            {"input_file": mesh_file, "output_file": "sphere.obj"},
        )
    )
    assert obj_name == "sphere.obj"

    xyz_name = parse_tool_result(
        await call_tool(
            mcp_session,
            "convert_point_cloud_format",
            {"input_file": cloud_file, "output_file": "cloud.xyz"},
        )
    )
    assert xyz_name == "cloud.xyz"

    # Mesh processing pipeline
    simplified = parse_tool_result(
        await call_tool(
            mcp_session,
            "simplify_mesh",
            {"input_file": mesh_file, "output_file": "sphere_simplified.stl", "reduction": 0.25},
        )
    )
    assert simplified == "sphere_simplified.stl"

    transformed = parse_tool_result(
        await call_tool(
            mcp_session,
            "transform_mesh",
            {
                "input_file": mesh_file,
                "output_file": "sphere_transformed.stl",
                "translate": [0.1, 0.0, 0.0],
            },
        )
    )
    assert transformed == "sphere_transformed.stl"

    normals = parse_tool_result(
        await call_tool(
            mcp_session,
            "mesh_compute_normals",
            {"input_file": mesh_file, "output_file": "sphere_normals.stl"},
        )
    )
    assert normals == "sphere_normals.stl"

    smoothed = parse_tool_result(
        await call_tool(
            mcp_session,
            "mesh_filter_average",
            {"input_file": mesh_file, "output_file": "sphere_smooth.stl", "iterations": 1},
        )
    )
    assert smoothed == "sphere_smooth.stl"

    taubin = parse_tool_result(
        await call_tool(
            mcp_session,
            "mesh_filter_taubin",
            {"input_file": mesh_file, "output_file": "sphere_taubin.stl", "iterations": 1},
        )
    )
    assert taubin == "sphere_taubin.stl"

    assert parse_tool_result(
        await call_tool(mcp_session, "mesh_is_watertight", {"input_file": mesh_file})
    ) is True
    assert parse_tool_result(
        await call_tool(mcp_session, "mesh_is_manifold", {"input_file": mesh_file})
    ) is True
    assert parse_tool_result(
        await call_tool(mcp_session, "mesh_is_orientable", {"input_file": mesh_file})
    ) is True
    assert isinstance(
        parse_tool_result(
            await call_tool(mcp_session, "mesh_is_self_intersecting", {"input_file": mesh_file})
        ),
        bool,
    )

    cleaned = parse_tool_result(
        await call_tool(
            mcp_session,
            "mesh_cleanup",
            {"input_file": mesh_file, "output_file": "sphere_clean.stl"},
        )
    )
    assert cleaned == "sphere_clean.stl"

    samples = parse_tool_result(
        await call_tool(
            mcp_session,
            "sample_mesh_surface",
            {
                "input_file": mesh_file,
                "output_file": "sphere_samples.pcd",
                "num_points": 5000,
            },
        )
    )
    assert samples == "sphere_samples.pcd"

    downsampled = parse_tool_result(
        await call_tool(
            mcp_session,
            "downsample_point_cloud",
            {
                "input_file": cloud_file,
                "output_file": "cloud_down.pcd",
                "voxel_size": 0.05,
            },
        )
    )
    assert downsampled == "cloud_down.pcd"

    transformed_cloud = parse_tool_result(
        await call_tool(
            mcp_session,
            "transform_point_cloud",
            {
                "input_file": cloud_file,
                "output_file": "cloud_transformed.pcd",
                "translate": [0.1, 0.0, 0.0],
            },
        )
    )
    assert transformed_cloud == "cloud_transformed.pcd"

    reconstructed = parse_tool_result(
        await call_tool(
            mcp_session,
            "reconstruct_mesh_from_point_cloud",
            {
                "input_file": "sphere_samples.pcd",
                "output_file": "reconstructed.stl",
                "depth": 6,
            },
        )
    )
    assert reconstructed == "reconstructed.stl"

    bounds = mesh_info["bounds"]
    crop_bounds = {
        "x": bounds["x"] + bounds["w"] * 0.25,
        "y": bounds["y"] + bounds["h"] * 0.25,
        "z": bounds["z"] + bounds["d"] * 0.25,
        "w": bounds["w"] * 0.5,
        "h": bounds["h"] * 0.5,
        "d": bounds["d"] * 0.5,
    }
    cropped = parse_tool_result(
        await call_tool(
            mcp_session,
            "crop_mesh",
            {
                "input_file": mesh_file,
                "output_file": "sphere_cropped.stl",
                "aabb": crop_bounds,
            },
        )
    )
    assert cropped == "sphere_cropped.stl"

    # Volume / surface
    volume = parse_tool_result(
        await call_tool(mcp_session, "compute_volume", {"input_file": mesh_file})
    )
    assert volume > 0

    cavities = parse_tool_result(
        await call_tool(mcp_session, "detect_cavities", {"input_file": mesh_file})
    )
    assert isinstance(cavities, list)

    cavity_output = parse_tool_result(
        await call_tool(
            mcp_session,
            "extract_cavity",
            {
                "input_file": mesh_file,
                "output_file": "cavity.pcd",
                "aabb": crop_bounds,
                "voxel_size": 0.1,
            },
        )
    )
    assert cavity_output == "cavity.pcd"

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_server}/workspace")
        response.raise_for_status()
        workspace_root = Path(response.json()["ws_path"])

    mesh = read_triangle_mesh(workspace_root / mesh_file).to_legacy()
    vertices = o3d.utility.Vector3dVector(mesh.vertices)
    point_a = vertices[0].tolist()
    point_b = vertices[min(1, len(vertices) - 1)].tolist()

    distance = parse_tool_result(
        await call_tool(
            mcp_session,
            "measure_surface_distance",
            {"input_file": mesh_file, "a": point_a, "b": point_b},
        )
    )
    assert distance >= 0

    area = parse_tool_result(
        await call_tool(
            mcp_session,
            "measure_surface_area",
            {"input_file": mesh_file, "bounds": bounds},
        )
    )
    assert area > 0

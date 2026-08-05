import os

import httpx

from common.types import (
    AABB,
    AppState,
    GeometryMeshConvertRequest,
    GeometryMeshSupportedRequest,
    GeometryMeshSupportedResponse,
    GeometryPointCloudSupportedRequest,
    GeometryPointCloudSupportedResponse,
    VolumeGetResponse,
    VolumeSetRequest,
    WorkspaceDownloadRequest,
    WorkspaceDownloadResponse,
    WorkspaceFilesResponse,
    WorkspaceRemoveRequest,
    WorkspaceRemoveResponse,
    WorkspaceResponse,
    WorkspaceUploadRequest,
    WorkspaceUploadResponse,
)

_client: httpx.AsyncClient | None = None


def _get_base_url() -> str:
    url = os.environ.get("MCP_LOCAL_API_URL")
    if not url:
        raise RuntimeError("MCP_LOCAL_API_URL environment variable is not set")
    return url


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client


########################################################
# State

async def state() -> AppState:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/state")
    response.raise_for_status()
    return AppState.model_validate(response.json())


########################################################
# Volume

async def volume_get() -> AABB | None:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/volume/get")
    response.raise_for_status()
    return VolumeGetResponse.model_validate(response.json()).volume


async def volume_set(volume: AABB | None = None) -> None:
    client = _get_client()
    payload = VolumeSetRequest(volume=volume)
    response = await client.post(
        f"{_get_base_url()}/volume/set",
        json=payload.model_dump(),
    )
    response.raise_for_status()


########################################################
# Workspace

async def workspace() -> str:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/workspace")
    response.raise_for_status()
    return WorkspaceResponse.model_validate(response.json()).ws_path


async def workspace_files() -> list[str]:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/workspace/files")
    response.raise_for_status()
    return WorkspaceFilesResponse.model_validate(response.json()).files


async def workspace_upload(file_paths: list[str]) -> WorkspaceUploadResponse:
    client = _get_client()
    payload = WorkspaceUploadRequest(file_paths=file_paths)
    response = await client.post(
        f"{_get_base_url()}/workspace/upload",
        json=payload.model_dump(),
    )
    response.raise_for_status()
    return WorkspaceUploadResponse.model_validate(response.json())


async def workspace_download(file_name: str, download_path: str) -> WorkspaceDownloadResponse:
    client = _get_client()
    payload = WorkspaceDownloadRequest(file_name=file_name, download_path=download_path)
    response = await client.post(
        f"{_get_base_url()}/workspace/download",
        json=payload.model_dump(),
    )
    response.raise_for_status()
    return WorkspaceDownloadResponse.model_validate(response.json())


async def workspace_remove(files: list[str]) -> WorkspaceRemoveResponse:
    client = _get_client()
    payload = WorkspaceRemoveRequest(files=files)
    response = await client.request(
        "DELETE",
        f"{_get_base_url()}/workspace/remove",
        json=payload.model_dump(),
    )
    response.raise_for_status()
    return WorkspaceRemoveResponse.model_validate(response.json())


########################################################
# Geometry

async def geometry_mesh_supported(file_path: str) -> bool:
    client = _get_client()
    payload = GeometryMeshSupportedRequest(file_path=file_path)
    response = await client.post(
        f"{_get_base_url()}/geometry/mesh/supported",
        json=payload.model_dump(),
    )
    response.raise_for_status()
    return GeometryMeshSupportedResponse.model_validate(response.json()).is_supported


async def geometry_point_cloud_supported(file_path: str) -> bool:
    client = _get_client()
    payload = GeometryPointCloudSupportedRequest(file_path=file_path)
    response = await client.post(
        f"{_get_base_url()}/geometry/point-cloud/supported",
        json=payload.model_dump(),
    )
    response.raise_for_status()
    return GeometryPointCloudSupportedResponse.model_validate(response.json()).is_supported


async def geometry_mesh_convert(src_path: str, dst_path: str) -> dict:
    client = _get_client()
    payload = GeometryMeshConvertRequest(src_path=src_path, dst_path=dst_path)
    response = await client.post(
        f"{_get_base_url()}/geometry/mesh/convert",
        json=payload.model_dump(),
    )
    response.raise_for_status()
    return response.json()

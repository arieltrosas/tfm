import os

import httpx

from common.types import (
    AppState,
    AABB,
    VolumeGetResponse,
    VolumeSetRequest,
    WorkspaceResponse,
    WorkspaceFilesResponse,
    WorkspaceUploadRequest,
    WorkspaceUploadResponse,
    WorkspaceRemoveRequest,
    WorkspaceDownloadRequest,
)

MCP_LOCAL_API_URL = os.environ["MCP_LOCAL_API_URL"]


async def api_state() -> AppState:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/state")
        response.raise_for_status()
        return AppState.model_validate(response.json())


async def api_workspace() -> WorkspaceResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/workspace")
        response.raise_for_status()
        return WorkspaceResponse.model_validate(response.json())


async def api_workspace_files() -> WorkspaceFilesResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/workspace/files")
        response.raise_for_status()
        return WorkspaceFilesResponse.model_validate(response.json())


async def api_workspace_upload(file_path: str) -> WorkspaceUploadResponse:
    payload = WorkspaceUploadRequest(file_path=file_path)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_LOCAL_API_URL}/workspace/upload",
            json=payload.model_dump()
        )
        response.raise_for_status()
        return WorkspaceUploadResponse.model_validate(response.json())


async def api_workspace_remove(file_name: str) -> None:
    payload = WorkspaceRemoveRequest(file_name=file_name)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "DELETE",
            f"{MCP_LOCAL_API_URL}/workspace/remove",
            json=payload.model_dump()
        )
        response.raise_for_status()


async def api_workspace_download(file_name: str, download_path: str) -> None:
    payload = WorkspaceDownloadRequest(file_name=file_name, download_path=download_path)
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{MCP_LOCAL_API_URL}/workspace/download",
            json=payload.model_dump()
        )
        response.raise_for_status()


async def api_volume_get() -> VolumeGetResponse:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_LOCAL_API_URL}/volume/get")
        response.raise_for_status()
        return VolumeGetResponse.model_validate(response.json())


async def api_volume_set(volume: AABB | None = None) -> None:
    payload = VolumeSetRequest(volume=volume)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_LOCAL_API_URL}/volume/set",
            json=payload.model_dump()
        )
        response.raise_for_status()

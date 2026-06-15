import os

import httpx

from common.types import (
    AABB,
    AppState,
    VolumeGetResponse,
    VolumeSetRequest,
    WorkspaceFilesResponse,
    WorkspaceResponse,
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


async def get_state() -> AppState:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/state")
    response.raise_for_status()
    return AppState.model_validate(response.json())


async def get_workspace_root() -> str:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/workspace")
    response.raise_for_status()
    return WorkspaceResponse.model_validate(response.json()).ws_path


async def list_files() -> list[str]:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/workspace/files")
    response.raise_for_status()
    return WorkspaceFilesResponse.model_validate(response.json()).files


async def get_volume() -> AABB | None:
    client = _get_client()
    response = await client.get(f"{_get_base_url()}/volume/get")
    response.raise_for_status()
    return VolumeGetResponse.model_validate(response.json()).volume


async def set_volume(volume: AABB | None = None) -> None:
    client = _get_client()
    payload = VolumeSetRequest(volume=volume)
    response = await client.post(
        f"{_get_base_url()}/volume/set",
        json=payload.model_dump(),
    )
    response.raise_for_status()

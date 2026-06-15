from fastapi import APIRouter, HTTPException

from common.types import (
    WorkspaceDownloadRequest,
    WorkspaceFilesResponse,
    WorkspaceRemoveRequest,
    WorkspaceResponse,
    WorkspaceUploadRequest,
    WorkspaceUploadResponse,
)
from api.dependencies import ServicesDep

router = APIRouter(tags=["workspace"])


@router.get("/workspace", response_model=WorkspaceResponse)
async def workspace(services: ServicesDep) -> WorkspaceResponse:
    return WorkspaceResponse(ws_path=str(services.workspace.root))


@router.get("/workspace/files", response_model=WorkspaceFilesResponse)
async def workspace_files(services: ServicesDep) -> WorkspaceFilesResponse:
    return WorkspaceFilesResponse(files=services.workspace.list_files())


@router.post("/workspace/upload", response_model=WorkspaceUploadResponse)
async def workspace_upload(
    request: WorkspaceUploadRequest, services: ServicesDep
) -> WorkspaceUploadResponse:
    try:
        file_name = await services.workspace.upload(request.file_path)
        return WorkspaceUploadResponse(file_name=file_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/workspace/remove")
async def workspace_remove(request: WorkspaceRemoveRequest, services: ServicesDep) -> dict:
    try:
        await services.workspace.remove(request.file_name)
        return {"status": "ok"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/workspace/download")
async def workspace_download(request: WorkspaceDownloadRequest, services: ServicesDep) -> dict:
    try:
        await services.workspace.download(request.file_name, request.download_path)
        return {"status": "ok"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")

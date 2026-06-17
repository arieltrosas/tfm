from api.dependencies import ServicesDep
from common.types import (
    WorkspaceDownloadRequest,
    WorkspaceDownloadResponse,
    WorkspaceFilesResponse,
    WorkspaceRemoveRequest,
    WorkspaceRemoveResponse,
    WorkspaceResponse,
    WorkspaceUploadRequest,
    WorkspaceUploadResponse,
)
from fastapi import APIRouter, HTTPException, Response, status

router = APIRouter(tags=["workspace"])


def _set_multi_status(response: Response, total: int, failed: int) -> None:
    if failed == total and total > 0:
        response.status_code = status.HTTP_400_BAD_REQUEST
    elif failed > 0:
        response.status_code = status.HTTP_207_MULTI_STATUS
    else:
        response.status_code = status.HTTP_200_OK


@router.get("/workspace", response_model=WorkspaceResponse)
async def workspace(services: ServicesDep) -> WorkspaceResponse:
    return WorkspaceResponse(ws_path=str(services.workspace.root))


@router.get("/workspace/files", response_model=WorkspaceFilesResponse)
async def workspace_files(services: ServicesDep) -> WorkspaceFilesResponse:
    return WorkspaceFilesResponse(files=services.workspace.list_files())


@router.post("/workspace/upload", response_model=WorkspaceUploadResponse, status_code=status.HTTP_200_OK)
async def workspace_upload(
    services: ServicesDep,
    request: WorkspaceUploadRequest,
    response: Response,
) -> WorkspaceUploadResponse:
    try:
        results = await services.workspace.upload(request.file_paths)
        failed_count = sum(1 for result in results.values() if result.status == "error")
        _set_multi_status(response, len(request.file_paths), failed_count)
        return WorkspaceUploadResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/workspace/download", response_model=WorkspaceDownloadResponse)
async def workspace_download(
    services: ServicesDep,
    request: WorkspaceDownloadRequest,
) -> WorkspaceDownloadResponse:
    try:
        result = await services.workspace.download(request.file_name, request.download_path)
        return WorkspaceDownloadResponse(result=result, download_path=request.download_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.delete("/workspace/remove", response_model=WorkspaceRemoveResponse, status_code=status.HTTP_200_OK)
async def workspace_remove(
    services: ServicesDep,
    request: WorkspaceRemoveRequest,
    response: Response,
) -> WorkspaceRemoveResponse:
    try:
        results = await services.workspace.remove(request.files)
        failed_count = sum(1 for result in results.values() if result.status == "error")
        _set_multi_status(response, len(request.files), failed_count)
        return WorkspaceRemoveResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

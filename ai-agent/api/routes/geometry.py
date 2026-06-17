from api.dependencies import ServicesDep
from common.types import (
    GeometryMeshConvertRequest,
    GeometryMeshSupportedRequest,
    GeometryMeshSupportedResponse,
    GeometryPointCloudSupportedRequest,
    GeometryPointCloudSupportedResponse,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["geometry"])


@router.post("/geometry/mesh/supported", response_model=GeometryMeshSupportedResponse)
async def is_mesh_supported(services: ServicesDep, request: GeometryMeshSupportedRequest) -> GeometryMeshSupportedResponse:
    return GeometryMeshSupportedResponse(is_supported=services.geometry.is_supported_mesh_file(request.file_path))


@router.post("/geometry/point-cloud/supported", response_model=GeometryPointCloudSupportedResponse)
async def is_point_cloud_supported(services: ServicesDep, request: GeometryPointCloudSupportedRequest) -> GeometryPointCloudSupportedResponse:
    return GeometryPointCloudSupportedResponse(is_supported=services.geometry.is_supported_point_cloud_file(request.file_path))


@router.post("/geometry/mesh/convert")
async def convert_mesh(
    services: ServicesDep,
    request: GeometryMeshConvertRequest,
) -> None:
    try:
        services.geometry.convert_mesh(request.src_path, request.dst_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IsADirectoryError:
        raise HTTPException(status_code=400, detail=f"File '{request.src_path}' is a directory")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"File '{request.src_path}' is not a valid mesh file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

from fastapi import APIRouter

from common.types import VolumeGetResponse, VolumeSetRequest
from api.dependencies import ServicesDep

router = APIRouter(tags=["volume"])


@router.get("/volume/get", response_model=VolumeGetResponse)
async def volume_get(services: ServicesDep) -> VolumeGetResponse:
    return VolumeGetResponse(volume=services.state.selected_volume)


@router.post("/volume/set")
async def volume_set(request: VolumeSetRequest, services: ServicesDep) -> dict:
    await services.state.set_volume(request.volume)
    return {"status": "ok"}

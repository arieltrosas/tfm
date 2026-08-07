from fastapi import APIRouter, HTTPException

from common.types import SelectionAddRequest, SelectionRemoveRequest
from api.dependencies import ServicesDep

router = APIRouter(tags=["selection"])


@router.post("/selection/add")
async def selection_add(request: SelectionAddRequest, services: ServicesDep) -> dict:
    await services.state.add_selections(request.selections)
    return {"status": "ok"}


@router.post("/selection/remove")
async def selection_remove(request: SelectionRemoveRequest, services: ServicesDep) -> dict:
    missing = await services.state.remove_selections(request.labels)
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Selections not found: {', '.join(missing)}",
        )
    return {"status": "ok"}

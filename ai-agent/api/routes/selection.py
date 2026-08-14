from fastapi import APIRouter, HTTPException

from common.types import (
    SelectionAddRequest,
    SelectionRemoveRequest,
    SelectionRenameRequest,
)
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


@router.post("/selection/rename")
async def selection_rename(request: SelectionRenameRequest, services: ServicesDep) -> dict:
    try:
        await services.state.rename_selection(request.old_label, request.new_label)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Selection not found: {request.old_label}",
        )
    except ValueError as exc:
        status_code = 400 if "empty" in str(exc) else 409
        raise HTTPException(status_code=status_code, detail=str(exc))
    return {"status": "ok"}

from fastapi import APIRouter

from common.types import AppState
from api.dependencies import ServicesDep

router = APIRouter(tags=["state"])


@router.get("/state", response_model=AppState)
async def get_app_state(services: ServicesDep) -> AppState:
    return services.state.get_snapshot()

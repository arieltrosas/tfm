from fastapi import APIRouter, HTTPException

from common.types import ModelListResponse, ModelResponse, ModelSetRequest
from api.dependencies import ServicesDep

router = APIRouter(tags=["model"])


@router.get("/model", response_model=ModelResponse)
async def model(services: ServicesDep) -> ModelResponse:
    return ModelResponse(model=services.mcp_client.model)


@router.get("/model/list", response_model=ModelListResponse)
async def model_list(services: ServicesDep) -> ModelListResponse:
    models = await services.mcp_client.list_models()
    return ModelListResponse(models=models)


@router.post("/model/set")
async def model_set(request: ModelSetRequest, services: ServicesDep) -> dict:
    models = await services.mcp_client.list_models()
    if request.model not in models:
        raise HTTPException(status_code=404, detail=f"Model '{request.model}' is not available")
    services.mcp_client.model = request.model
    return {"status": "ok"}

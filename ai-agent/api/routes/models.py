from fastapi import APIRouter, HTTPException

from common.types import ModelListResponse, ModelResponse, ModelSetRequest
from mcp_client.client import ProviderNotConnected
from api.dependencies import ServicesDep

router = APIRouter(tags=["model"])


@router.get("/model", response_model=ModelResponse)
async def model(services: ServicesDep) -> ModelResponse:
    return ModelResponse(model=services.mcp_client.model)


@router.get("/model/list", response_model=ModelListResponse)
async def model_list(services: ServicesDep) -> ModelListResponse:
    try:
        models = await services.mcp_client.list_models()
        return ModelListResponse(models=models)
    except ProviderNotConnected:
        return ModelListResponse(models=[])


@router.post("/model/set")
async def model_set(request: ModelSetRequest, services: ServicesDep) -> dict:
    try:
        models = await services.mcp_client.list_models()
    except ProviderNotConnected:
        raise HTTPException(status_code=503, detail="No LLM provider connected")

    if request.model not in models:
        raise HTTPException(status_code=404, detail=f"Model '{request.model}' is not available")
    services.mcp_client.model = request.model
    return {"status": "ok"}

from fastapi import APIRouter, HTTPException

from common.types import ConnectOllamaRequest, ConnectOpenAIRequest
from api.dependencies import ServicesDep

router = APIRouter(tags=["connect"])


@router.post("/connect/ollama")
async def connect_ollama(request: ConnectOllamaRequest, services: ServicesDep) -> dict:
    try:
        await services.mcp_client.connect_ollama_client(host=request.host, key=request.key)
        return {"status": "connected to ollama"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/openai")
async def connect_openai(request: ConnectOpenAIRequest, services: ServicesDep) -> dict:
    try:
        await services.mcp_client.connect_openai_client(
            base_url=request.base_url, api_key=request.api_key
        )
        return {"status": "connected to openai"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

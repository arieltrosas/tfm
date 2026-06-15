from fastapi import APIRouter, HTTPException

from common.types import ChatRequest, ChatResponse
from api.dependencies import ServicesDep

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, services: ServicesDep) -> ChatResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = await services.mcp_client.process_chat_query(request.query)
        return ChatResponse(response=result)
    except Exception as e:
        services.mcp_client.logger.error(f"Error processing query via HTTP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

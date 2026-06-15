import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from common.events import AppEvent, AppEventType
from api.dependencies import ServicesDep

router = APIRouter(tags=["events"])

HEARTBEAT_INTERVAL_SECONDS = 20


async def _event_stream(services: ServicesDep) -> AsyncIterator[str]:
    snapshot = services.state.get_snapshot()
    initial = AppEvent(
        type=AppEventType.APP_STATE_CHANGED,
        payload=snapshot.model_dump(),
    )
    yield f"data: {json.dumps(initial.model_dump(mode='json'))}\n\n"

    subscription = services.events.subscribe()
    aiter = subscription.__aiter__()

    while True:
        try:
            event = await asyncio.wait_for(
                aiter.__anext__(),
                timeout=HEARTBEAT_INTERVAL_SECONDS,
            )
            yield f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
        except asyncio.TimeoutError:
            yield ": heartbeat\n\n"
        except StopAsyncIteration:
            break


@router.get("/events")
async def events(services: ServicesDep) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(services),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

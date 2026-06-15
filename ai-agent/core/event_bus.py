import asyncio
from collections.abc import AsyncIterator

from common.events import AppEvent


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[AppEvent | None]] = []

    async def publish(self, event: AppEvent) -> None:
        for queue in self._subscribers:
            await queue.put(event)

    async def subscribe(self) -> AsyncIterator[AppEvent]:
        queue: asyncio.Queue[AppEvent | None] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self._subscribers.remove(queue)

    async def close_subscriber(self, queue: asyncio.Queue[AppEvent | None]) -> None:
        await queue.put(None)

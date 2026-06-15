from common.events import AppEvent, AppEventType
from common.types import AABB, AppState
from core.event_bus import EventBus
from core.workspace import WorkspaceService


class StateService:
    def __init__(self, workspace: WorkspaceService, event_bus: EventBus) -> None:
        self._workspace = workspace
        self._event_bus = event_bus
        self._selected_volume: AABB | None = None

    def get_snapshot(self) -> AppState:
        return AppState(
            workspace_dir=str(self._workspace.root),
            files=self._workspace.list_files(),
            selected_volume=self._selected_volume,
        )

    async def set_volume(self, volume: AABB | None) -> None:
        self._selected_volume = volume
        payload: dict = {"volume": volume.model_dump() if volume else None}
        await self._event_bus.publish(
            AppEvent(type=AppEventType.VOLUME_CHANGED, payload=payload)
        )

    @property
    def selected_volume(self) -> AABB | None:
        return self._selected_volume

from common.events import AppEvent, AppEventType
from common.types import AppState, Selection
from core.event_bus import EventBus
from core.workspace import WorkspaceService


class StateService:
    def __init__(self, workspace: WorkspaceService, event_bus: EventBus) -> None:
        self._workspace = workspace
        self._event_bus = event_bus
        self._selections: dict[str, Selection] = {}

    def get_snapshot(self) -> AppState:
        return AppState(
            workspace_dir=str(self._workspace.root),
            files=self._workspace.list_files(),
            selections=self._selections,
        )

    async def add_selections(self, selections: dict[str, Selection]) -> None:
        if not selections:
            return
        self._selections.update(selections)
        await self._publish_selections_changed()

    async def remove_selections(self, labels: list[str]) -> list[str]:
        """Remove selections by label. Returns labels that were not found."""
        missing = [label for label in labels if label not in self._selections]
        if missing:
            return missing
        if not labels:
            return []
        for label in labels:
            del self._selections[label]
        await self._publish_selections_changed()
        return []

    async def rename_selection(self, old_label: str, new_label: str) -> None:
        """Rename a selection label, preserving its data and dict order."""
        if old_label == new_label:
            return
        if old_label not in self._selections:
            raise KeyError(old_label)
        if not new_label:
            raise ValueError("New label must not be empty")
        if new_label in self._selections:
            raise ValueError(f"Selection already exists: {new_label}")
        self._selections = {
            (new_label if label == old_label else label): selection
            for label, selection in self._selections.items()
        }
        await self._publish_selections_changed()

    async def _publish_selections_changed(self) -> None:
        payload = {"selections": self.get_snapshot().model_dump()["selections"]}
        await self._event_bus.publish(
            AppEvent(type=AppEventType.SELECTION_CHANGED, payload=payload)
        )

    @property
    def selections(self) -> dict[str, Selection]:
        return self._selections

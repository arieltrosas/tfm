import shutil
import tempfile
from pathlib import Path

from common.events import AppEvent, AppEventType
from core.event_bus import EventBus


class WorkspaceService:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._container = tempfile.TemporaryDirectory(prefix="mcp_workspace_")
        self._root = Path(self._container.name).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def cleanup(self) -> None:
        self._container.cleanup()

    def list_files(self) -> list[str]:
        return sorted(path.name for path in self._root.iterdir() if path.is_file())

    def resolve_file(self, filename: str) -> Path:
        candidate = (self._root / filename).resolve()
        if not candidate.is_relative_to(self._root):
            raise ValueError("Path escapes workspace")
        if not candidate.is_file():
            raise FileNotFoundError(f"File '{filename}' not found")
        return candidate

    async def _emit_files_changed(self) -> None:
        files = self.list_files()
        await self._event_bus.publish(
            AppEvent(
                type=AppEventType.WORKSPACE_FILES_CHANGED,
                payload={"files": files},
            )
        )

    async def upload(self, source_path: str) -> str:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"File '{source_path}' not found")

        target = self._root / source.name
        if target.exists():
            stem = target.stem
            n = 0
            while target.exists():
                target = target.with_stem(f"{stem} ({n})")
                n += 1

        shutil.copy(source, target)
        await self._emit_files_changed()
        return target.name

    async def remove(self, file_name: str) -> None:
        path = self.resolve_file(file_name)
        path.unlink()
        await self._emit_files_changed()

    async def download(self, file_name: str, download_path: str) -> None:
        src_path = self.resolve_file(file_name)
        shutil.copy(src_path, Path(download_path))

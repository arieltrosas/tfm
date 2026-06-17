import shutil
import tempfile
from pathlib import Path

from common.events import AppEvent, AppEventType
from common.types import FileResult
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

    async def upload(self, src_paths: list[str]) -> dict[str, FileResult]:
        results: dict[str, FileResult] = {}

        def generate_dst_path(src: Path) -> Path:
            dst = self._root / src.name
            if dst.exists():
                stem, n = dst.stem, 0
                while dst.exists():
                    dst = dst.with_stem(f"{stem} ({n})")
                    n += 1
            return dst

        def upload_file(src_path: str) -> Path:
            path = Path(src_path)
            if not path.exists():
                raise FileNotFoundError(f"File '{path}' not found")
            dst_path = generate_dst_path(path)
            shutil.copy(path, dst_path)
            return dst_path

        for src_path in src_paths:
            try:
                dst_path = upload_file(src_path)
                results[src_path] = FileResult(
                    file_name=dst_path.name,
                    status="success",
                )
            except Exception as e:
                results[src_path] = FileResult(
                    file_name=Path(src_path).name,
                    status="error",
                    error=str(e),
                )

        await self._emit_files_changed()
        return results

    async def download(self, file_name: str, download_path: str) -> FileResult:
        src_path = self.resolve_file(file_name)
        shutil.copy(src_path, Path(download_path))
        return FileResult(file_name=file_name, status="success")

    async def remove(self, files: list[str]) -> dict[str, FileResult]:
        results: dict[str, FileResult] = {}

        for file_name in files:
            try:
                path = self.resolve_file(file_name)
                path.unlink(missing_ok=True)
                results[file_name] = FileResult(file_name=file_name, status="success")
            except Exception as e:
                results[file_name] = FileResult(
                    file_name=file_name,
                    status="error",
                    error=str(e),
                )

        await self._emit_files_changed()
        return results

from pathlib import Path

from .api_client import get_workspace_root
from .common import resolve_existing_file, resolve_output_target


def resolve_input_file(root: Path, filename: str) -> Path:
    return resolve_existing_file(root, filename)


def resolve_output_file(root: Path, filename: str) -> Path:
    return resolve_output_target(root, filename)


async def _get_workspace_root_path() -> Path:
    return Path(await get_workspace_root())


async def resolve_workspace_input(filename: str) -> Path:
    root = await _get_workspace_root_path()
    return resolve_input_file(root, filename)


async def resolve_workspace_output(filename: str) -> Path:
    root = await _get_workspace_root_path()
    return resolve_output_file(root, filename)


async def write_workspace_text(filename: str, content: str) -> Path:
    output_path = await resolve_workspace_output(filename)
    output_path.write_text(content, encoding="utf-8")
    return output_path

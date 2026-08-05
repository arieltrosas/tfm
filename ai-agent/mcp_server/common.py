from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

def resolve_within_root(root: Path, filename: str) -> Path:
    root = root.resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid workspace path")
    return path

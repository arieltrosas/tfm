from pathlib import Path


def resolve_workspace_file(root: Path, filename: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / filename).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError("Path escapes workspace")
    if not candidate.is_file():
        raise FileNotFoundError(f"File '{filename}' not found")
    return candidate

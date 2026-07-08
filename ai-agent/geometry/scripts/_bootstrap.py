"""Import helper for standalone scripts in geometry/scripts/."""

import sys
from pathlib import Path

_AI_AGENT_ROOT = Path(__file__).resolve().parents[2]


def setup() -> Path:
    """Ensure ai-agent is on sys.path so `geometry.*` imports work."""
    root = str(_AI_AGENT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return _AI_AGENT_ROOT

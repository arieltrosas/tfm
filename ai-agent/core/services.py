from dataclasses import dataclass

from mcp_client.client import MCPClient

from core.event_bus import EventBus
from core.state import StateService
from core.workspace import WorkspaceService


@dataclass
class AppServices:
    workspace: WorkspaceService
    state: StateService
    events: EventBus
    mcp_client: MCPClient

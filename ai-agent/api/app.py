from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.event_bus import EventBus
from core.services import AppServices
from core.state import StateService
from core.workspace import WorkspaceService
from mcp_client.client import MCPClient

from api.routes import chat, connect, events, health, models, shutdown, state, volume, workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_bus = EventBus()
    workspace = WorkspaceService(event_bus)
    state_service = StateService(workspace, event_bus)
    mcp_client = MCPClient()

    print(f"MCP Workspace physical directory created at '{workspace.root}'")

    app.state.services = AppServices(
        workspace=workspace,
        state=state_service,
        events=event_bus,
        mcp_client=mcp_client,
    )

    yield

    workspace.cleanup()
    # NOTE: mcp_client.cleanup() is intentionally handled inside main.py
    # to avoid AnyIO cross-task cancel scope violations.


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.include_router(state.router)
    app.include_router(volume.router)
    app.include_router(chat.router)
    app.include_router(connect.router)
    app.include_router(health.router)
    app.include_router(workspace.router)
    app.include_router(models.router)
    app.include_router(shutdown.router)
    app.include_router(events.router)

    return app

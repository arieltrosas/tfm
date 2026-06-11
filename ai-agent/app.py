# app.py

import os
import signal
import tempfile
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from mcp_client.client import MCPClient, OllamaClientAuthError

# Centralized data structures and request/response models
from common.types import (
    AppState,
    AABB,
    VolumeGetResponse,
    VolumeSetRequest,
    ChatRequest,
    ChatResponse,
    AuthRequest,
    HealthResponse,
    WorkspaceResponse,
    WorkspaceFilesResponse,
    WorkspaceUploadRequest,
    WorkspaceUploadResponse,
    WorkspaceRemoveRequest,
    WorkspaceDownloadRequest,
    ModelResponse,
    ModelListResponse,
    ModelSetRequest,
)

# -----------------------------------------------------------------------------
# App Configuration & Lifecycle

mcp_client = MCPClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize temporary workspace directory structure
    app.state._workspace_container = tempfile.TemporaryDirectory(prefix="mcp_workspace_")
    ws_path = str(Path(app.state._workspace_container.name).absolute())
    print(f"MCP Workspace physical directory created at '{ws_path}'")

    # 2. Initialize the centralized AppState object
    app.state.app_state = AppState(
        workspace_dir=ws_path,
        selected_volume=None
    )

    yield

    # Shutdown and cleanup workspace filesystem resources
    app.state._workspace_container.cleanup()
    # NOTE: mcp_client.cleanup() is intentionally handled inside main.py 
    # to avoid AnyIO cross-task cancel scope violations.


app = FastAPI(lifespan=lifespan)

# -----------------------------------------------------------------------------
# Application State Endpoint

@app.get("/state", response_model=AppState)
async def get_app_state():
    return app.state.app_state


# -----------------------------------------------------------------------------
# Volume Endpoints

@app.get("/volume/get", response_model=VolumeGetResponse)
async def volume_get():
    return VolumeGetResponse(volume=app.state.app_state.selected_volume)


@app.post("/volume/set")
async def volume_set(request: VolumeSetRequest):
    app.state.app_state.selected_volume = request.volume


# -----------------------------------------------------------------------------
# Chat Endpoint

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = await mcp_client.process_chat_query(request.query)
        return ChatResponse(response=result)
    except Exception as e:
        mcp_client.logger.error(f"Error processing query via HTTP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# -----------------------------------------------------------------------------
# Auth Endpoint

@app.post("/auth")
async def auth(request: AuthRequest):
    try:
        await mcp_client.connect_ollama_client(host=request.host, key=request.key)
    except OllamaClientAuthError:
        raise HTTPException(status_code=401, detail="Could not authenticate to Ollama")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# -----------------------------------------------------------------------------
# Health Endpoint

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy")


# -----------------------------------------------------------------------------
# Workspace Endpoints

@app.get("/workspace", response_model=WorkspaceResponse)
async def workspace():
    return WorkspaceResponse(ws_path=app.state.app_state.workspace_dir)


@app.get("/workspace/files", response_model=WorkspaceFilesResponse)
async def workspace_files():
    ws_path = Path(app.state.app_state.workspace_dir)
    files = [path.name for path in ws_path.iterdir() if path.is_file()]
    return WorkspaceFilesResponse(files=files)


@app.post("/workspace/upload", response_model=WorkspaceUploadResponse)
async def workspace_upload(request: WorkspaceUploadRequest):
    source_path = Path(request.file_path)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{request.file_path}' not found")

    ws_path = Path(app.state.app_state.workspace_dir)
    target_path = ws_path / source_path.name

    if target_path.exists():
        stem = target_path.stem
        n = 0
        while target_path.exists():
            target_path = target_path.with_stem(f"{stem} ({n})")
            n = n + 1

    shutil.copy(source_path, target_path)
    return WorkspaceUploadResponse(file_name=target_path.name)


@app.delete("/workspace/remove")
async def workspace_remove(request: WorkspaceRemoveRequest):
    path = Path(app.state.app_state.workspace_dir) / request.file_name
    try:
        path.unlink()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/workspace/download")
async def workspace_download(request: WorkspaceDownloadRequest):
    ws_path = Path(app.state.app_state.workspace_dir)
    src_path = ws_path / request.file_name
    dst_path = Path(request.download_path)

    if not src_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")

    shutil.copy(src_path, dst_path)


# -----------------------------------------------------------------------------
# Model Endpoints

@app.get("/model", response_model=ModelResponse)
async def model():
    return ModelResponse(model=mcp_client.model)


@app.get("/model/list", response_model=ModelListResponse)
async def model_list():
    models = await mcp_client.list_models()
    return ModelListResponse(models=models)


@app.post("/model/set")
async def model_set(request: ModelSetRequest):
    models = await mcp_client.list_models()
    if not request.model in models:
        raise HTTPException(status_code=404, detail=f"Model '{request.model}' is not available")
    mcp_client.model = request.model


# -----------------------------------------------------------------------------
# Shutdown Endpoint

@app.post("/shutdown")
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)

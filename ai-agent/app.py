# app.py

import os, signal, time
import tempfile
import shutil

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from mcp_client.client import MCPClient, OllamaClientAuthError
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# App

mcp_client = MCPClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup

    # init workspace

    app.state.workspace = tempfile.TemporaryDirectory(prefix="mcp_workspace_")
    ws_path = str(Path(app.state.workspace.name).absolute())
    print(f"MCP Workspace created at '{ws_path}'")

    # init MCP

    try:
        await mcp_client.connect_ollama_client()
        models = await mcp_client.list_models()
        if models:
            mcp_client.model = models[0]

        await mcp_client.connect_mcp_server(workspace_dir=ws_path)
    except Exception as e:
        print(f"Error during startup configuration: {e}")

    yield

    # Shutdown

    app.state.workspace.cleanup()
    await mcp_client.cleanup()


app = FastAPI(lifespan=lifespan)

# -----------------------------------------------------------------------------
# Chat Endpoint

class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


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

class AuthRequest(BaseModel):
    host: str
    key: str

@app.post("/auth")
async def auth(request: AuthRequest):
    try:
        await mcp_client.connect_ollama_client(host=request.host, key=request.key)
    except OllamaClientAuthError:
        raise HTTPException(status_code=401, detail=f"Could not authenticate to Ollama")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# -----------------------------------------------------------------------------
# Health Endpoint

class HealthResponse(BaseModel):
    status: str

@app.get("/health")
async def health():
    return HealthResponse(status="healthy")


# -----------------------------------------------------------------------------
# Workspace Endpoint

class WorkspaceResponse(BaseModel):
    ws_path: str


@app.get("/workspace", response_model=WorkspaceResponse)
async def workspace():
    return WorkspaceResponse(ws_path=app.state.workspace.name)


# -----------------------------------------------------------------------------
# Workspace Files Endpoint

class WorkspaceFilesResponse(BaseModel):
    files: list[str]


@app.get("/workspace/files", response_model=WorkspaceFilesResponse)
async def workspace_files():
    ws_path = Path(app.state.workspace.name)
    files = [path.name for path in ws_path.iterdir() if path.is_file()]
    return WorkspaceFilesResponse(files=files)


# -----------------------------------------------------------------------------
# Workspace Upload Endpoint

class WorkspaceUploadRequest(BaseModel):
    file_path: str


class WorkspaceUploadResponse(BaseModel):
    file_name: str


@app.post("/workspace/upload", response_model=WorkspaceUploadResponse)
async def workspace_upload(request: WorkspaceUploadRequest):
    source_path = Path(request.file_path)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{request.file_path}' not found")

    ws_path = Path(app.state.workspace.name)
    target_path = ws_path / source_path.name

    if target_path.exists():
        stem = target_path.stem
        n = 0
        while target_path.exists():
            target_path = target_path.with_stem(f"{stem} ({n})")
            n = n + 1

    if target_path.exists():
        raise HTTPException(status_code=500, detail=f"Interal Server Error")

    shutil.copy(source_path, target_path)
    return WorkspaceUploadResponse(file_name=target_path.name)


# -----------------------------------------------------------------------------
# Workspace Remove Endpoint

class WorkspaceRemoveRequest(BaseModel):
    file_name: str


@app.delete("/workspace/remove")
async def workspace_remove(request: WorkspaceRemoveRequest):
    path = Path(app.state.workspace.name) / request.file_name
    try:
        path.unlink()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")
    except Exception:
        raise HTTPException(status_code=500, detail=f"Interal Server Error")


# -----------------------------------------------------------------------------
# Workspace Download Endpoint

class WorkspaceDownloadRequest(BaseModel):
    file_name: str
    download_path: str


@app.get("/workspace/download")
async def workspace_download(request: WorkspaceDownloadRequest):
    ws_path = Path(app.state.workspace.name)
    src_path = ws_path / request.file_name
    dst_path = Path(request.download_path)

    if not src_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{request.file_name}' not found")

    shutil.copy(src_path, dst_path)


# -----------------------------------------------------------------------------
# Model Endpoint

class ModelResponse(BaseModel):
    model: str


@app.get("/model", response_model=ModelResponse)
async def model():
    return ModelResponse(model=mcp_client.model)


# -----------------------------------------------------------------------------
# Model List Endpoint

class ModelListResponse(BaseModel):
    models: list[str]


@app.get("/model/list")
async def model_list():
    models = await mcp_client.list_models()
    return ModelListResponse(models=models)


# -----------------------------------------------------------------------------
# Model Set Endpoint

class ModelSetRequest(BaseModel):
    model: str


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

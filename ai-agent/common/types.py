# common/types.py

from pydantic import BaseModel

# --- Core Objects ---

class AABB(BaseModel):
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float


class AppState(BaseModel):
    workspace_dir: str
    files: list[str]
    selected_volume: AABB | None


# --- Connection Endpoints Schemas ---

class ConnectOllamaRequest(BaseModel):
    host: str | None = None
    key: str | None = None


class ConnectOpenAIRequest(BaseModel):
    base_url: str
    api_key: str


# --- Volume Endpoints Schemas ---

class VolumeGetResponse(BaseModel):
    volume: AABB | None


class VolumeSetRequest(BaseModel):
    volume: AABB | None


# --- Chat Endpoints Schemas ---

class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


# --- Healthcheck Endpoints Schemas ---

class HealthResponse(BaseModel):
    status: str


# --- Workspace Endpoints Schemas ---

class WorkspaceResponse(BaseModel):
    ws_path: str


class WorkspaceFilesResponse(BaseModel):
    files: list[str]


class WorkspaceUploadRequest(BaseModel):
    file_path: str


class WorkspaceUploadResponse(BaseModel):
    file_name: str


class WorkspaceRemoveRequest(BaseModel):
    file_name: str


class WorkspaceDownloadRequest(BaseModel):
    file_name: str
    download_path: str


# --- Model Endpoints Schemas ---

class ModelResponse(BaseModel):
    model: str


class ModelListResponse(BaseModel):
    models: list[str]


class ModelSetRequest(BaseModel):
    model: str

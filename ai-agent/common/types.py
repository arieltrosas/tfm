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
    selected_volume: AABB | None


# --- Volume Endpoints Schemas ---

class VolumeGetResponse(BaseModel):
    volume: AABB | None


class VolumeSetRequest(BaseModel):
    volume: AABB | None


# --- Chat & Auth Endpoints Schemas ---

class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


class AuthRequest(BaseModel):
    host: str
    key: str


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

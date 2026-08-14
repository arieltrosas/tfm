# common/types.py

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# --- Core Objects ---

class AABB(BaseModel):
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float


class Point(BaseModel):
    x: float
    y: float
    z: float


class AabbSelection(BaseModel):
    kind: Literal["aabb"]
    aabb: AABB


class PointSelection(BaseModel):
    kind: Literal["point"]
    point: Point


Selection = Annotated[AabbSelection | PointSelection, Field(discriminator="kind")]


class AppState(BaseModel):
    workspace_dir: str
    files: list[str]
    selections: dict[str, Selection]


# --- Connection Endpoints Schemas ---

class ConnectOllamaRequest(BaseModel):
    host: str | None = None
    key: str | None = None


class ConnectOpenAIRequest(BaseModel):
    base_url: str
    api_key: str


# --- Selection Endpoints Schemas ---

class SelectionAddRequest(BaseModel):
    selections: dict[str, Selection]


class SelectionRemoveRequest(BaseModel):
    labels: list[str]


class SelectionRenameRequest(BaseModel):
    old_label: str
    new_label: str


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


class FileResult(BaseModel):
    file_name: str
    status: str
    error: str | None = None


class WorkspaceUploadRequest(BaseModel):
    file_paths: list[str]


class WorkspaceUploadResponse(BaseModel):
    results: dict[str, FileResult]


class WorkspaceRemoveRequest(BaseModel):
    files: list[str]


class WorkspaceRemoveResponse(BaseModel):
    results: dict[str, FileResult]


class WorkspaceDownloadRequest(BaseModel):
    file_name: str
    download_path: str


class WorkspaceDownloadResponse(BaseModel):
    result: FileResult
    download_path: str


# --- Model Endpoints Schemas ---

class ModelResponse(BaseModel):
    model: str


class ModelListResponse(BaseModel):
    models: list[str]


class ModelSetRequest(BaseModel):
    model: str


# --- Geometry Endpoints Schemas ---

class GeometryMeshSupportedRequest(BaseModel):
    file_path: str


class GeometryMeshSupportedResponse(BaseModel):
    is_supported: bool


class GeometryPointCloudSupportedRequest(BaseModel):
    file_path: str


class GeometryPointCloudSupportedResponse(BaseModel):
    is_supported: bool


class GeometryMeshConvertRequest(BaseModel):
    src_path: str
    dst_path: str

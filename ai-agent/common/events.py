from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class AppEventType(str, Enum):
    WORKSPACE_FILES_CHANGED = "workspace.files_changed"
    VOLUME_CHANGED = "volume.changed"
    APP_STATE_CHANGED = "app_state.changed"


class AppEvent(BaseModel):
    type: AppEventType
    payload: dict
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

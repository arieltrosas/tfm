import asyncio
import json
import os
import signal

from fastapi import APIRouter

router = APIRouter(tags=["shutdown"])


@router.post("/shutdown")
def shutdown() -> dict:
    os.kill(os.getpid(), signal.SIGINT)
    return {"status": "shutting down"}

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, suppress
from pathlib import Path

import httpx
import pytest_asyncio
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from api.app import create_app
from geometry.io import write_point_cloud, write_triangle_mesh
from tests.helpers.assets import cloud_as_tensor_point_cloud, sphere_as_tensor_mesh

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = PROJECT_ROOT / "main.py"


@pytest_asyncio.fixture
async def tandem() -> AsyncIterator[tuple[str, ClientSession, dict[str, str]]]:
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=0, loop="asyncio")
    server = uvicorn.Server(config)
    stack = AsyncExitStack()

    serve_task = asyncio.create_task(server.serve())
    try:
        while not server.started:
            await asyncio.sleep(0.05)

        port = 8000
        for srv in server.servers:
            for sock in srv.sockets:
                port = sock.getsockname()[1]
                break

        base_url = f"http://127.0.0.1:{port}"

        async with httpx.AsyncClient() as client:
            for _ in range(50):
                try:
                    response = await client.get(f"{base_url}/health")
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.05)
            else:
                raise RuntimeError("API server failed to become healthy")

            response = await client.get(f"{base_url}/workspace")
            response.raise_for_status()
            workspace_root = Path(response.json()["ws_path"])

        filenames = {"mesh": "sphere.ply", "cloud": "cloud.pcd"}
        mesh = sphere_as_tensor_mesh()
        point_cloud = cloud_as_tensor_point_cloud(mesh.to_legacy(), num_points=1000)
        write_triangle_mesh(workspace_root / filenames["mesh"], mesh)
        write_point_cloud(workspace_root / filenames["cloud"], point_cloud)

        os.environ["MCP_LOCAL_API_URL"] = base_url
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(MAIN_PY), "server"],
            env=os.environ.copy(),
        )

        transport = await stack.enter_async_context(stdio_client(server_params))
        read_stream, write_stream = transport
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        yield base_url, session, filenames
    finally:
        with suppress(RuntimeError, Exception):
            await stack.aclose()
        server.should_exit = True
        serve_task.cancel()
        with suppress(asyncio.CancelledError):
            await serve_task


@pytest_asyncio.fixture
async def api_server(tandem: tuple[str, ClientSession, dict[str, str]]) -> str:
    return tandem[0]


@pytest_asyncio.fixture
async def mcp_session(tandem: tuple[str, ClientSession, dict[str, str]]) -> ClientSession:
    return tandem[1]


@pytest_asyncio.fixture
async def seed_workspace(tandem: tuple[str, ClientSession, dict[str, str]]) -> dict[str, str]:
    return tandem[2]

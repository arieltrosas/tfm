# main.py

def run_mcp_client(port_file: str | None):
    import asyncio
    import uvicorn
    from app import app

    port = 0 if port_file is not None else 8000

    async def serve():
        config = uvicorn.Config(
            app, 
            host="127.0.0.1", 
            port=port, 
            workers=1, 
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        
        server_task = asyncio.create_task(server.serve())
        
        while not server.started:
            await asyncio.sleep(0.05)
            
        actual_port = port
        if port == 0:
            try:
                for srv in server.servers:
                    for sock in srv.sockets:
                        actual_port = sock.getsockname()[1]
                        break
            except Exception as e:
                print(f"Warning: Could not resolve dynamic port from sockets: {e}")

        if port_file is not None:
            try:
                with open(port_file, "w") as f:
                    f.write(str(actual_port))
            except Exception as e:
                print(f"Warning: Could not write to port file: {e}")

        await server_task

    asyncio.run(serve())


def run_mcp_server(workspace_dir: str):
    os.environ["MCP_WORKSPACE_DIR"] = workspace_dir

    import mcp_server as server
    server.mcp.run(transport="stdio")


if __name__ == "__main__":
    import argparse, os

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True, help="App")

    run_client = subparsers.add_parser("client", help="Runs the MCP Client")
    run_client.add_argument("port_file", type=str, nargs="?", default=None, help="Port handshake file. If not given, defaults to port 8000")

    run_server = subparsers.add_parser("server", help="Runs the MCP Server on Stdio Transport")
    run_server.add_argument("workspace_dir", type=str, help="Path to the Workspace Directory")

    args = parser.parse_args()

    try:
        if args.mode == "client":
            run_mcp_client(args.port_file)
        elif args.mode == "server":
            run_mcp_server(args.workspace_dir)
    except KeyboardInterrupt:
        os._exit(0)

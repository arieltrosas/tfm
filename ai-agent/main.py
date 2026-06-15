# main.py

import os
import argparse
import asyncio

def run_mcp_client(port_file: str | None):
    import uvicorn
    from app import app, mcp_client

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

        # 1. Record the confirmed local API URL into the environment
        os.environ["MCP_LOCAL_API_URL"] = f"http://127.0.0.1:{actual_port}"
        print(f"API Live! Exposed environment variable: MCP_LOCAL_API_URL={os.environ['MCP_LOCAL_API_URL']}")

        # 2. Wrap client components lifecycle in a try/finally block within the same task context
        try:
            # await mcp_client.connect_ollama_client()
            # models = await mcp_client.list_models()
            # if models:
            #     mcp_client.model = models[0]
            #
            await mcp_client.connect_mcp_server()
            
            # Keep this task context alive until Uvicorn winds down
            await server_task
            
        except asyncio.CancelledError:
            # Catching the cancellation signal triggered during server shutdown sequence
            pass
        except Exception as e:
            print(f"Error during application execution loop: {e}")
        finally:
            # Tear down everything within the exact task context it was spawned in
            print("\nShutting down MCP Client sub-processes and sessions cleanly...")
            try:
                await mcp_client.cleanup()
            except Exception as cleanup_err:
                print(f"Warning: Issue encountered during connection cleanup: {cleanup_err}")
            print("Cleanup complete. Server stopped.")

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


def run_mcp_server():
    import mcp_server as server
    server.mcp.run(transport="stdio")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True, help="App")

    run_client = subparsers.add_parser("client", help="Runs the MCP Client")
    run_client.add_argument("port_file", type=str, nargs="?", default=None, help="Port handshake file. If not given, defaults to port 8000")

    run_server = subparsers.add_parser("server", help="Runs the MCP Server on Stdio Transport")

    args = parser.parse_args()

    if args.mode == "client":
        run_mcp_client(args.port_file)
    elif args.mode == "server":
        try:
            run_mcp_server()
        except KeyboardInterrupt:
            os._exit(0)

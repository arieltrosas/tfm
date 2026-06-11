# mcp_client/client.py

import sys, os

from .logger import setup_client_logger

from typing import Optional, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent
from mcp.client.stdio import stdio_client

from ollama import ChatResponse, Message, Tool, ResponseError
from ollama import AsyncClient as OllamaClient

# -----------------------------------------------------------------------------
# Exceptions


class MCPClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to the MCP server """
    pass


class OllamaClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to Ollama """ 
    pass

class OllamaClientAuthError(Exception):
    """ Raised when the MCP client fails to authenticate to Ollama """
    pass

# -----------------------------------------------------------------------------
# Utility


def _mcp_server_command() -> tuple[str, list[str]]:
    command: str
    args: list[str]

    if getattr(sys, "frozen", False):
        command = sys.executable
        args = ["server"]
    else:
        command = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        args = [script_path, "server"]

    return command, args


# -----------------------------------------------------------------------------
# MCPClient


class MCPClient:
    """
    MCPClient Class
    Handles chat queries, tools, resource and system prompts for the agent
    """

    def __init__(self):
        self.model: str = ""
        self.chat: list[Message] = []
        self.tools: list[Tool] = []
        self.ollama_client: Optional[OllamaClient] = None
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.logger = setup_client_logger()

    
    async def list_models(self) -> list[str]:
        if not self.ollama_client:
            raise OllamaClientNotConnected("Could not find an Ollama connection")
        response = await self.ollama_client.list()
        return [m.model for m in response.models if m.model]


    async def cleanup(self):
        """
        Clean up client resources.
        """
        await self.exit_stack.aclose()


    async def connect_ollama_client(self, host: str | None = None, key: str | None = None):
        """
        Creates the Ollama client connection.
        """
        self.ollama_client = OllamaClient(host=host, headers = {"Authorization": f"Bearer {key}"})
        try:
            await self.ollama_client.list()
        except ResponseError as e:
            if e.status_code == 401:
                raise OllamaClientAuthError("Could not authenticate to Ollama provider")
            else:
                raise OllamaClientNotConnected(f"Could not connect to Ollama provider ({e.status_code}): {e.error}")
        except Exception as e:
                raise Exception(f"Internal Server Error")


    async def connect_mcp_server(self):
        """
        Spawns the MCP server process and connects the client to the MCP server.
        """

        # 1. Start the MCP server & create a session

        env = os.environ.copy()

        command, args = _mcp_server_command()

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # 2. Discover Tools

        self.tools = [
            Tool.model_validate({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema
                }
            })
            for t in (await self.session.list_tools()).tools
        ]

        self.logger.info(
            self.tools, 
            extra={
                "event_type": "tools_discovery", 
                "model_used": self.model or "not_selected_yet"
            }
        )


    async def process_chat_query(self, query: str) -> str:
        """
        Process a chat query and gives back a response.
        """

        if not self.session:
            raise MCPClientNotConnected("Could not find an active MCP server session")

        if not self.ollama_client:
            raise OllamaClientNotConnected("Could not find an Ollama connection")

        # 1. Enforce the presence of the strategic Contextual System Prompt
        system_content = (
            "You are an expert AI assistant tightly connected to a Model Context Protocol (MCP) server "
            "built for 3D geometric processing and engineering calculations.\n"
            "You have direct access to an active processing workspace and centralized application state through "
            "your exposed tools.\n"
            "CRITICAL OPERATIONAL NOTICE: The internal workspace file directory and active application variables "
            "are highly volatile and subject to modification outside of this direct conversation history. "
            "You must frequently and deliberately execute your tools to inspect and validate the actual, AT EACH INTERACTION WITH THE USER "
            "to be sure of the state of the workspace (e.g., listing tracked files, validating application state) before giving a response, "
            "forming execution assumptions or running complex calculations."
        )

        # Inject or repair system prompt placement at the beginning of the context loop
        if not self.chat or self.chat[0].role != 'system':
            self.chat.insert(0, Message(role='system', content=system_content))
        else:
            # Keep it fresh/updated if system parameters adjust
            self.chat[0] = Message(role='system', content=system_content)

        # 2. Append incoming user action query
        initial_message = Message(role='user', content=query)
        self.chat.append(initial_message)

        while True: # tool_call_loop
            response: ChatResponse = await self.ollama_client.chat(
                model=self.model,
                messages=self.chat,
                tools=self.tools,
                think=True,
            )

            self.chat.append(response.message)

            if not response.message.tool_calls:
                break

            for tc in response.message.tool_calls:
                tool_name = tc.function.name
                tool_args = tc.function.arguments

                try:
                    result = await self.session.call_tool(tool_name, arguments=dict(tool_args))
                    content = "\n".join([c.text for c in result.content if isinstance(c, TextContent)])
                except Exception as e:
                    content = f"Error executing tool {tool_name}: {str(e)}"

                self.chat.append(Message(role='tool', content=content, tool_name=tool_name))

        self.logger.info(
            {"chat": self.chat},
            extra={
                "event_type": "chat_context_snapshot", 
                "model_used": self.model
            }
        )

        return str(self.chat[-1].content)

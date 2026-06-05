# mcp_client/client.py

import sys, os

from .logger import setup_client_logger

from typing import Optional, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent
from mcp.client.stdio import stdio_client

from ollama import ChatResponse, Message, Tool
from ollama import AsyncClient as OllamaClient

# -----------------------------------------------------------------------------
# Exceptions


class MCPClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to the MCP server """
    pass


class OllamaClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to Ollama """ 
    pass

# -----------------------------------------------------------------------------
# Utility


def _mcp_server_command(workspace_dir: str) -> tuple[str, list[str]]:
    command: str
    args: list[str]

    if getattr(sys, "frozen", False):
        command = sys.executable
        args = ["server", workspace_dir]
    else:
        command = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        args = [script_path, "server", workspace_dir]

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


    def connect_ollama_client(self, host: str | None = None):
        """
        Creates the Ollama client connection.
        """
        self.ollama_client = OllamaClient(host=host)


    async def connect_mcp_server(self, workspace_dir: str):
        """
        Spawns the MCP server process and connects the client to the MCP server.

        Arguments:
            mcp_server_module: Name of the python module that will run the mcp server.
            workspace_dir: Path of the workspace temporary dir assigned to the server.
        """

        # 1. Start the MCP server & create a session

        env = os.environ.copy()

        command, args = _mcp_server_command(workspace_dir)

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

        Arguments:
            query: String containing the query to resolve.

        Returns:
            A string with the response.

        Raises:
            MCPClientNotConnected
            OllaClientNotConnected
        """

        # 0. Check client status

        if not self.session:
            raise MCPClientNotConnected("Could not find an active MCP server session")

        if not self.ollama_client:
            raise OllamaClientNotConnected("Could not find an Ollama connection")

        # 1. Prepare the first message and discover tools

        ## 1.1 Create the initial message and add it to the chat

        initial_message = Message(role='user', content=query)
        self.chat.append(initial_message) # TODO: create a chat window strategy to discard old chats

        # 2. Message Loop

        while True: # tool_call_loop


            ## 2.1 Send the message and wait for the response, then append the response to the chat

            response: ChatResponse = await self.ollama_client.chat(
                model=self.model,
                messages=self.chat,
                tools=self.tools,
                think=True, # TODO: refine thinking strategy
            )

            self.chat.append(response.message)

            # 2.2 If not tools are called, stop

            if not response.message.tool_calls:
                break # tool_call_loop

            # 2.3 Make all tools calls and append the results to the chat

            for tc in response.message.tool_calls:
                tool_name = tc.function.name
                tool_args = tc.function.arguments

                try:
                    result = await self.session.call_tool(tool_name, arguments=dict(tool_args))
                    content = "\n".join([c.text for c in result.content if isinstance(c, TextContent)])
                except Exception as e:
                    content = f"Error executing tool {tool_name}: {str(e)}"

                self.chat.append(Message(role='tool', content=content, tool_name=tool_name))

        # 3. Return the final response

        self.logger.info(
            {"chat": self.chat},
            extra={
                "event_type": "chat_context_snapshot", 
                "model_used": self.model
            }
        )

        return str(self.chat[-1].content)

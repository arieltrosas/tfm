# mcp_client/client.py

import sys
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Any, Literal
from contextlib import AsyncExitStack

from .logger import setup_client_logger

from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent
from mcp.client.stdio import stdio_client

# Ollama SDK Imports
from ollama import ChatResponse, ResponseError
from ollama import AsyncClient as OllamaClient

# OpenAI SDK Imports
from openai import AsyncOpenAI, OpenAIError

# -----------------------------------------------------------------------------
# Exceptions

class MCPClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to the MCP server """
    pass

class ProviderNotConnected(Exception):
    """ Raised when no model provider (Ollama or OpenAI) is connected """
    pass

class OllamaClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to Ollama """ 
    pass

class OllamaClientAuthError(Exception):
    """ Raised when the MCP client fails to authenticate to Ollama """
    pass

class OpenAIClientNotConnected(Exception):
    """ Raised when the MCP client cannot connect to OpenAI/OpenCode """
    pass

class OpenAIClientAuthError(Exception):
    """ Raised when the MCP client fails to authenticate to OpenAI/OpenCode """
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
# LLM Provider Adapters

class LLMProviderAdapter(ABC):
    """
    Abstract interface for LLM providers. Adapts provider-specific SDK responses
    to a standardized format expected by the MCPClient.
    """
    @abstractmethod
    async def list_models(self) -> list[str]:
        pass

    @abstractmethod
    async def generate(self, model: str, chat_history: list[dict[str, Any]], tools: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Returns a tuple containing:
        1. assistant_message: A standardized dictionary representing the assistant's reply.
        2. pending_tool_calls: A list of dicts with 'id', 'name', and 'arguments'.
        """
        pass

class OllamaAdapter(LLMProviderAdapter):
    def __init__(self, client: OllamaClient):
        self.client = client

    async def list_models(self) -> list[str]:
        response = await self.client.list()
        return [m.model for m in response.models if m.model]

    async def generate(self, model: str, chat_history: list[dict[str, Any]], tools: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        # Ollama SDK accepts raw dicts for messages/tools naturally
        response: ChatResponse = await self.client.chat(
            model=model,
            messages=chat_history, # type: ignore
            tools=tools if tools else None, # type: ignore
            think=True,
        )

        assistant_msg: dict[str, Any] = {
            "role": "assistant", 
            "content": response.message.content or ""
        }
        
        pending_tool_calls = []

        if response.message.tool_calls:
            assistant_msg["tool_calls"] = []
            for idx, tc in enumerate(response.message.tool_calls):
                call_id = f"call_{idx}"
                args_dict = tc.function.arguments if isinstance(tc.function.arguments, dict) else dict(tc.function.arguments)
                args_str = json.dumps(args_dict) if isinstance(args_dict, dict) else str(args_dict)

                assistant_msg["tool_calls"].append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args_str
                    }
                })

                pending_tool_calls.append({
                    "id": call_id,
                    "name": tc.function.name,
                    "arguments": args_dict
                })

        return assistant_msg, pending_tool_calls


class OpenAIAdapter(LLMProviderAdapter):
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def list_models(self) -> list[str]:
        response = await self.client.models.list()
        return [m.id for m in response.data if m.id]

    async def generate(self, model: str, chat_history: list[dict[str, Any]], tools: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        response = await self.client.chat.completions.create(
            model=model,
            messages=chat_history, # type: ignore
            tools=tools if tools else None # type: ignore
        )

        # 1. Safely dump the Pydantic-like object to a native dictionary immediately
        message_dict = response.choices[0].message.model_dump()

        assistant_msg: dict[str, Any] = {
            "role": "assistant", 
            "content": message_dict.get("content") or ""
        }
        
        pending_tool_calls = []

        if message_dict.get("tool_calls"):
            # 2. The dumped dictionary already matches the exact format we need
            assistant_msg["tool_calls"] = message_dict["tool_calls"]

            # 3. Iterate over the native dictionaries instead of SDK objects
            for tc in message_dict["tool_calls"]:
                try:
                    args_str = tc["function"].get("arguments")
                    args_dict = json.loads(args_str) if args_str else {}
                except Exception:
                    args_dict = {}

                pending_tool_calls.append({
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": args_dict
                })

        return assistant_msg, pending_tool_calls

# -----------------------------------------------------------------------------
# MCPClient

class MCPClient:
    """
    MCPClient Class
    Handles chat queries, tools, resource and system prompts for the agent.
    Delegates generation to an agnostic LLMProviderAdapter.
    """

    def __init__(self):
        self.model: str = ""
        self.provider: Optional[Literal["ollama", "openai"]] = None  
        self.adapter: Optional[LLMProviderAdapter] = None
        
        self.chat: list[dict[str, Any]] = []  
        self.tools: list[dict[str, Any]] = []  

        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.logger = setup_client_logger()

    def set_model(self, model_name: str):
        self.model = model_name

    async def list_models(self) -> list[str]:
        if not self.adapter:
            raise ProviderNotConnected("No active LLM provider connection found.")
        return await self.adapter.list_models()

    async def cleanup(self):
        await self.exit_stack.aclose()

    async def connect_ollama_client(self, host: str | None = None, key: str | None = None):
        client = OllamaClient(host=host, headers={"Authorization": f"Bearer {key}"} if key else None)

        try:
            self.adapter = OllamaAdapter(client)
            self.provider = "ollama"
            models = await self.list_models()
            self.model = models[0]
        except ResponseError as e:
            if e.status_code == 401:
                raise OllamaClientAuthError("Could not authenticate to Ollama provider")
            else:
                raise OllamaClientNotConnected(f"Could not connect to Ollama provider ({e.status_code}): {e.error}")
        except Exception:
            raise Exception("Internal Server Error connecting to Ollama")

    async def connect_openai_client(self, base_url: str, api_key: str):
        if not base_url.endswith("/"):
            base_url += "/"

        client = AsyncOpenAI(base_url=base_url, api_key=api_key)

        try:
            self.adapter = OpenAIAdapter(client)
            self.provider = "openai"
            models = await self.list_models()
            self.model = models[0]
        except OpenAIError as e:
            raise OpenAIClientAuthError(f"Could not authenticate/connect to OpenAI compatible provider: {str(e)}")
        except Exception as e:
            raise OpenAIClientNotConnected(f"Internal Server Error connecting to OpenAI context: {str(e)}")

    async def connect_mcp_server(self):
        env = os.environ.copy()
        command, args = _mcp_server_command()

        server_params = StdioServerParameters(command=command, args=args, env=env)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema
                }
            }
            for t in (await self.session.list_tools()).tools
        ]

        self.logger.info(
            self.tools, 
            extra={"event_type": "tools_discovery", "model_used": self.model or "not_selected_yet"}
        )

    async def process_chat_query(self, query: str) -> str:
        if not self.session:
            raise MCPClientNotConnected("Could not find an active MCP server session")

        if not self.adapter:
            raise ProviderNotConnected("No connected LLM client adapter found.")

        # Pre-fetch the application state via server tool directly before LLM interaction
        try:
            state_result = await self.session.call_tool("get_app_state", arguments={})
            state_json_str = "\n".join([c.text for c in state_result.content if isinstance(c, TextContent)])
            state_context = f"\n\nCURRENT RUNTIME APPLICATION STATE (Injected Context):\n{state_json_str}"
        except Exception as e:
            self.logger.error(f"Failed pre-fetching app state: {e}")
            state_context = "\n\nCURRENT RUNTIME APPLICATION STATE: [Unavailable due to retrieval failure]"

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

        # Merge core system instructions with the freshly collected state payload
        full_system_prompt = system_content + state_context

        system_message: dict[str, Any] = {"role": "system", "content": full_system_prompt}
        if not self.chat or self.chat[0].get('role') != 'system':
            self.chat.insert(0, system_message)
        else:
            self.chat[0] = system_message

        self.chat.append({"role": "user", "content": query})

        while True:
            assistant_msg, pending_tool_calls = await self.adapter.generate(
                self.model,
                self.chat, 
                self.tools
            )

            self.chat.append(assistant_msg)

            if not pending_tool_calls:
                break

            for tc in pending_tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]

                try:
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
                    content = "\n".join([c.text for c in result.content if isinstance(c, TextContent)])
                except Exception as e:
                    content = f"Error executing tool {tool_name}: {str(e)}"

                self.chat.append({
                    "role": "tool", 
                    "tool_call_id": tc["id"], 
                    "name": tool_name, 
                    "content": content
                })

        self.logger.info(
            {"chat": self.chat},
            extra={"event_type": "chat_context_snapshot", "model_used": self.model}
        )

        return str(self.chat[-1].get("content", ""))

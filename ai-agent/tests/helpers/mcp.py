import json
from typing import Any

from mcp import ClientSession
from mcp.types import CallToolResult, TextContent


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> CallToolResult:
    result = await session.call_tool(name, arguments or {})
    if result.isError:
        raise AssertionError(f"{name} failed: {result.content}")
    return result


def parse_tool_result(result: CallToolResult) -> Any:
    if result.structuredContent is not None:
        if "result" in result.structuredContent:
            return result.structuredContent["result"]
        return result.structuredContent

    text_parts: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent):
            text_parts.append(block.text)

    if not text_parts:
        return None

    text = "\n".join(text_parts)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text

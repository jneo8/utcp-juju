"""Adapter for the OpenAI Agents SDK."""

import json
from typing import Any

from agents import FunctionTool
from agents.tool_context import ToolContext

from utcp_juju.config import JujuConfig
from utcp_juju.toolset import JujuTools, ToolDef


def _function_tool(tool: ToolDef) -> FunctionTool:
    async def on_invoke_tool(_context: ToolContext[Any], arguments: str) -> str:
        try:
            parsed = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError as exc:
            return f'Error: arguments are not valid JSON: {exc}'
        return await tool.invoke(parsed)

    return FunctionTool(
        name=tool.name,
        description=tool.description,
        params_json_schema=tool.parameters,
        on_invoke_tool=on_invoke_tool,
        # Juju's schemas use open objects and optional fields, which strict mode forbids.
        strict_json_schema=False,
    )


def for_openai_agents(
    config: JujuConfig | None = None, *, tools: JujuTools | None = None
) -> list[FunctionTool]:
    """Return the Juju tools as ``FunctionTool`` objects."""
    return [_function_tool(tool) for tool in (tools or JujuTools(config)).tools()]

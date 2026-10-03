"""Adapter for Google ADK."""

from typing import Any

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from utcp_juju.config import JujuConfig
from utcp_juju.toolset import JujuTools, ToolDef


class JujuAdkTool(BaseTool):
    """An ADK tool backed by one Juju ``ToolDef``."""

    def __init__(self, tool: ToolDef) -> None:
        super().__init__(name=tool.name, description=tool.description)
        self._tool = tool

    def _get_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self._tool.parameters,
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        """Run the tool and return its JSON (or error) text."""
        return await self._tool.invoke(args)


def for_google_adk(
    config: JujuConfig | None = None, *, tools: JujuTools | None = None
) -> list[BaseTool]:
    """Return the Juju tools as ADK tools."""
    return [JujuAdkTool(tool) for tool in (tools or JujuTools(config)).tools()]

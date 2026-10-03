"""The UTCP communication protocol for ``juju`` call templates."""

import json
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from utcp.data.call_template import CallTemplate
from utcp.data.register_manual_response import RegisterManualResult
from utcp.data.utcp_manual import UtcpManualSerializer
from utcp.interfaces.communication_protocol import CommunicationProtocol

from utcp_juju.call_template import JujuCallTemplate
from utcp_juju.executor import JujuExecutor
from utcp_juju.manual import utcp_manual

if TYPE_CHECKING:
    from utcp.utcp_client import UtcpClient


class JujuCommunicationProtocol(CommunicationProtocol):
    """Executes Juju facade methods for a UTCP client."""

    def __init__(self, executor: JujuExecutor | None = None) -> None:
        self._executor = executor or JujuExecutor()

    async def register_manual(
        self, caller: 'UtcpClient', manual_call_template: CallTemplate
    ) -> RegisterManualResult:
        """Register the manual bundled with this package."""
        manual = UtcpManualSerializer().validate_dict(json.loads(utcp_manual().read_text()))
        return RegisterManualResult(
            manual_call_template=manual_call_template, manual=manual, success=True, errors=[]
        )

    async def deregister_manual(
        self, caller: 'UtcpClient', manual_call_template: CallTemplate
    ) -> None:
        """Nothing to release: connections live only for the duration of a call."""

    async def call_tool(
        self,
        caller: 'UtcpClient',
        tool_name: str,
        tool_args: dict[str, Any],
        tool_call_template: CallTemplate,
    ) -> Any:
        """Call one facade method and return its result as plain JSON data."""
        if not isinstance(tool_call_template, JujuCallTemplate):
            raise ValueError(f'{tool_name}: not a juju call template')
        return await self._executor.call(tool_call_template, tool_args)

    async def call_tool_streaming(
        self,
        caller: 'UtcpClient',
        tool_name: str,
        tool_args: dict[str, Any],
        tool_call_template: CallTemplate,
    ) -> AsyncGenerator[Any, None]:
        """Yield the single result of ``call_tool``; no Juju read method streams."""
        yield await self.call_tool(caller, tool_name, tool_args, tool_call_template)

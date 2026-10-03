"""The tool set in the framework-neutral form adapters map onto their own tool type."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import orjson

from utcp_juju.config import JujuConfig
from utcp_juju.errors import JujuError
from utcp_juju.executor import JujuExecutor
from utcp_juju.manual import ToolSpec, load_manual


@dataclass(frozen=True)
class ToolDef:
    """A framework-neutral function tool."""

    name: str
    description: str
    parameters: dict[str, Any]
    invoke: Callable[[dict[str, Any]], Awaitable[str]]


class JujuTools:
    """Read-only Juju tools backed by the bundled manual."""

    def __init__(
        self,
        config: JujuConfig | None = None,
        *,
        executor: JujuExecutor | None = None,
        specs: tuple[ToolSpec, ...] | None = None,
    ) -> None:
        self._executor = executor or JujuExecutor(config)
        self.specs = {spec.name: spec for spec in (specs or load_manual())}

    async def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an operation by manual name; raises ``JujuError`` on failure."""
        spec = self.specs.get(name)
        if spec is None:
            known = ', '.join(sorted(self.specs))
            raise JujuError(f'unknown operation {name!r}; available: {known}')
        return await self._executor.call(spec.template, arguments or {})

    async def call_text(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call an operation for an agent: JSON text, or the error as text."""
        try:
            return orjson.dumps(await self.call(name, arguments)).decode()
        except JujuError as exc:
            return f'Error: {exc.message}'

    def tools(self) -> list[ToolDef]:
        """One typed tool per operation, named ``juju_<facade>_<method>``."""

        def bind(name: str) -> Callable[[dict[str, Any]], Awaitable[str]]:
            async def invoke(arguments: dict[str, Any]) -> str:
                return await self.call_text(name, arguments)

            return invoke

        return [
            ToolDef(
                name='juju_' + spec.name.replace('.', '_'),
                description=spec.description,
                parameters=spec.inputs,
                invoke=bind(spec.name),
            )
            for spec in self.specs.values()
        ]

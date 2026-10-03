"""Access to the bundled UTCP manual."""

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from utcp_juju.call_template import JujuCallTemplate

MANUAL_NAME = 'juju.utcp.json'


@dataclass(frozen=True)
class ToolSpec:
    """One tool of the manual."""

    name: str
    description: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    tags: tuple[str, ...]
    template: JujuCallTemplate


def utcp_manual() -> Path:
    """Path of the bundled manual, for hosts that run their own UTCP client."""
    return Path(str(resources.files('utcp_juju') / 'data' / MANUAL_NAME))


def parse_manual(manual: dict[str, Any]) -> tuple[ToolSpec, ...]:
    """Parse a manual document into tool specs."""
    return tuple(
        ToolSpec(
            name=tool['name'],
            description=tool.get('description', ''),
            inputs=tool.get('inputs') or {'type': 'object', 'properties': {}},
            outputs=tool.get('outputs') or {},
            tags=tuple(tool.get('tags') or ()),
            template=JujuCallTemplate.model_validate(tool['tool_call_template']),
        )
        for tool in manual['tools']
    )


@cache
def load_manual() -> tuple[ToolSpec, ...]:
    """Tool specs of the bundled manual."""
    return parse_manual(json.loads(utcp_manual().read_text()))

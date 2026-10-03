"""The read-only allowlist: which facade methods become tools, and how."""

from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    # Reject unknown keys, so a misspelt option fails instead of being ignored.
    model_config = ConfigDict(extra='forbid', frozen=True)


class MethodEntry(_Strict):
    """One allowlisted method."""

    description: str = Field(min_length=1)
    default_params: dict[str, Any] = {}


class FacadeEntry(_Strict):
    """The allowlisted methods of one facade."""

    methods: dict[str, MethodEntry]


class Allowlist(_Strict):
    """The whole allowlist for one Juju series."""

    series: str = Field(pattern=r'^\d+\.\d+$')
    facades: dict[str, FacadeEntry]

    @classmethod
    def from_yaml(cls, text: str) -> 'Allowlist':
        """Parse and validate the YAML file."""
        return cls.model_validate(yaml.safe_load(text))

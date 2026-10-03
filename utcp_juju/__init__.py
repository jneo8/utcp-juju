"""Read-only Juju function tools for AI agents, generated from Juju's facade RPC schema."""

from utcp_juju.call_template import JujuCallTemplate, JujuCallTemplateSerializer
from utcp_juju.config import JujuConfig
from utcp_juju.errors import JujuError
from utcp_juju.executor import JujuExecutor
from utcp_juju.manual import ToolSpec, load_manual, utcp_manual
from utcp_juju.toolset import JujuTools, ToolDef


def register() -> None:
    """UTCP plugin entry point: register the ``juju`` call template."""
    from utcp.plugins.discovery import register_call_template

    register_call_template('juju', JujuCallTemplateSerializer())


__all__ = [
    'JujuCallTemplate',
    'JujuCallTemplateSerializer',
    'JujuConfig',
    'JujuError',
    'JujuExecutor',
    'JujuTools',
    'ToolDef',
    'ToolSpec',
    'load_manual',
    'register',
    'utcp_manual',
]

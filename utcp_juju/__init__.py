"""Read-only Juju function tools for AI agents, generated from Juju's facade RPC schema."""

from utcp_juju.call_template import JujuCallTemplate, JujuCallTemplateSerializer
from utcp_juju.manual import ToolSpec, load_manual, utcp_manual


def register() -> None:
    """UTCP plugin entry point: register the ``juju`` call template."""
    from utcp.plugins.discovery import register_call_template

    register_call_template('juju', JujuCallTemplateSerializer())


__all__ = [
    'JujuCallTemplate',
    'JujuCallTemplateSerializer',
    'ToolSpec',
    'load_manual',
    'register',
    'utcp_manual',
]

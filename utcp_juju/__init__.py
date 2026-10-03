"""Read-only Juju function tools for AI agents, generated from Juju's facade RPC schema."""

from utcp_juju.call_template import JujuCallTemplate, JujuCallTemplateSerializer
from utcp_juju.config import JujuConfig
from utcp_juju.errors import JujuError
from utcp_juju.executor import JujuExecutor
from utcp_juju.manual import ToolSpec, load_manual, utcp_manual
from utcp_juju.toolset import JujuTools, ToolDef


def register() -> None:
    """UTCP plugin entry point: register the ``juju`` protocol and call template."""
    from utcp.plugins.discovery import register_call_template, register_communication_protocol

    from utcp_juju.protocol import JujuCommunicationProtocol

    register_communication_protocol('juju', JujuCommunicationProtocol())
    register_call_template('juju', JujuCallTemplateSerializer())


def for_openai_agents(config: JujuConfig | None = None) -> list:
    """Tools for the OpenAI Agents SDK. Needs the ``openai-agents`` extra."""
    from utcp_juju.adapters.openai_agents import for_openai_agents as build

    return build(config)


def for_google_adk(config: JujuConfig | None = None) -> list:
    """Tools for Google ADK. Needs the ``google-adk`` extra."""
    from utcp_juju.adapters.google_adk import for_google_adk as build

    return build(config)


__all__ = [
    'JujuCallTemplate',
    'JujuCallTemplateSerializer',
    'JujuConfig',
    'JujuError',
    'JujuExecutor',
    'JujuTools',
    'ToolDef',
    'ToolSpec',
    'for_google_adk',
    'for_openai_agents',
    'load_manual',
    'register',
    'utcp_manual',
]

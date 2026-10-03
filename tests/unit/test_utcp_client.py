import pytest
from utcp.plugins.discovery import register_communication_protocol
from utcp.utcp_client import UtcpClient

from utcp_juju import JujuExecutor, load_manual, utcp_manual
from utcp_juju.protocol import JujuCommunicationProtocol


@pytest.fixture
def juju_protocol(config):
    """Point the registered protocol at the fake controller for one test."""
    register_communication_protocol(
        'juju', JujuCommunicationProtocol(JujuExecutor(config)), override=True
    )
    yield
    register_communication_protocol('juju', JujuCommunicationProtocol(), override=True)


async def tool_names(client):
    return {tool.name for tool in await client.search_tools('', limit=1000)}


async def test_juju_manual_template_registers_the_bundled_manual(controller, juju_protocol):
    client = await UtcpClient.create(
        config={'manual_call_templates': [{'name': 'juju', 'call_template_type': 'juju'}]}
    )
    names = await tool_names(client)
    assert len(names) == len(load_manual())
    assert 'juju.client.full_status' in names

    controller.respond('Client.FullStatus', {'model': {'name': 'prod'}})
    result = await client.call_tool('juju.client.full_status', {'model': 'prod'})
    assert result == {'model': {'name': 'prod'}}


async def test_file_template_needs_the_juju_protocol_allowed():
    def template(**extra):
        return {
            'manual_call_templates': [
                {
                    'name': 'juju',
                    'call_template_type': 'file',
                    'file_path': str(utcp_manual()),
                    **extra,
                }
            ]
        }

    allowed = await UtcpClient.create(config=template(allowed_communication_protocols=['juju']))
    assert len(await tool_names(allowed)) == len(load_manual())

    filtered = await UtcpClient.create(config=template())
    assert await tool_names(filtered) == set()

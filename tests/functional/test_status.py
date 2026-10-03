"""`client.full_status` against a real controller, as a user with only `read`."""

import dataclasses
import json

import jubilant
import pytest
from utcp.plugins.discovery import register_communication_protocol
from utcp.utcp_client import UtcpClient

from utcp_juju import (
    JujuConfig,
    JujuError,
    JujuExecutor,
    JujuTools,
    for_google_adk,
    for_openai_agents,
    load_manual,
)
from utcp_juju.connection import JujuConnection
from utcp_juju.protocol import JujuCommunicationProtocol

from .conftest import Deployment

FULL_STATUS = 'client.full_status'


async def test_full_status_agrees_with_juju_status(
    juju: jubilant.Juju, tools: JujuTools, deployment: Deployment
):
    result = await tools.call(FULL_STATUS, {'model': deployment.model})

    expected = juju.status()
    assert result['model']['name'] == deployment.model
    assert result['model']['version'] == expected.model.version
    assert set(result['applications']) == set(expected.apps)
    app = result['applications'][deployment.app]
    assert app['status']['status'] == expected.apps[deployment.app].app_status.current
    assert set(app['units']) == set(expected.apps[deployment.app].units)


async def test_result_keys_are_declared_in_the_manual(tools: JujuTools, deployment: Deployment):
    (spec,) = (spec for spec in load_manual() if spec.name == FULL_STATUS)
    result = await tools.call(FULL_STATUS, {'model': deployment.model})
    assert set(result) <= set(spec.outputs['properties'])


async def test_patterns_narrow_the_result(tools: JujuTools, deployment: Deployment):
    matching = await tools.call(
        FULL_STATUS, {'model': deployment.model, 'patterns': [deployment.app]}
    )
    assert set(matching['applications']) == {deployment.app}
    other = await tools.call(FULL_STATUS, {'model': deployment.model, 'patterns': ['no-such-app']})
    assert not other.get('applications')


async def test_model_can_be_named_three_ways(
    juju: jubilant.Juju, tools: JujuTools, deployment: Deployment
):
    info = juju.show_model()
    by_name = await tools.call(FULL_STATUS, {'model': deployment.model})
    # ModelInfo.name is the qualified `owner/name`.
    for model in (info.model_uuid, info.name):
        result = await tools.call(FULL_STATUS, {'model': model})
        assert result['model']['name'] == by_name['model']['name']
        assert set(result['applications']) == set(by_name['applications'])


async def test_unknown_model_is_an_error_text_for_the_agent(
    tools: JujuTools, deployment: Deployment
):
    text = await tools.call_text(FULL_STATUS, {'model': 'no-such-model'})
    assert text.startswith("Error: model 'no-such-model' not found")
    assert deployment.model in text


async def test_wrong_password_is_refused(reader_config: JujuConfig, deployment: Deployment):
    wrong = dataclasses.replace(reader_config, password='not-the-password')
    with pytest.raises(JujuError, match='invalid entity name or password'):
        await JujuTools(wrong).call(FULL_STATUS, {'model': deployment.model})


async def test_wrong_ca_certificate_is_refused(reader_config: JujuConfig, deployment: Deployment):
    # No CA configured: verification falls back to the system trust store, which does not
    # know the controller's self-signed CA.
    untrusted = dataclasses.replace(reader_config, ca_cert=None)
    with pytest.raises(JujuError, match='cannot connect'):
        await JujuTools(untrusted).call(FULL_STATUS, {'model': deployment.model})


async def test_controller_refuses_a_write_from_the_read_only_user(
    juju: jubilant.Juju, reader_config: JujuConfig, deployment: Deployment
):
    """The second layer of the read-only guarantee: even a hand-built write is denied."""
    uuid = juju.show_model().model_uuid
    async with await JujuConnection.open(reader_config, uuid) as connection:
        version = max(connection.facades['Application'])
        change = {'application': deployment.app, 'generation': 'master', 'config': {}}
        with pytest.raises(JujuError, match='permission denied'):
            await connection.request('Application', version, 'SetConfigs', {'Args': [change]})


async def test_openai_agents_tool(reader_config: JujuConfig, deployment: Deployment):
    (tool,) = for_openai_agents(reader_config)
    result = json.loads(await tool.on_invoke_tool(None, json.dumps({'model': deployment.model})))
    assert deployment.app in result['applications']


async def test_google_adk_tool(reader_config: JujuConfig, deployment: Deployment):
    (tool,) = for_google_adk(reader_config)
    text = await tool.run_async(args={'model': deployment.model}, tool_context=None)
    assert deployment.app in json.loads(text)['applications']


async def test_utcp_client(reader_config: JujuConfig, deployment: Deployment):
    register_communication_protocol(
        'juju', JujuCommunicationProtocol(JujuExecutor(reader_config)), override=True
    )
    try:
        client = await UtcpClient.create(
            config={'manual_call_templates': [{'name': 'juju', 'call_template_type': 'juju'}]}
        )
        result = await client.call_tool('juju.client.full_status', {'model': deployment.model})
    finally:
        register_communication_protocol('juju', JujuCommunicationProtocol(), override=True)
    assert deployment.app in result['applications']

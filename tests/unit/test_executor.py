import pytest

from utcp_juju import JujuConfig, JujuError, JujuExecutor, JujuTools, load_manual

from .conftest import MODEL_UUID

(FULL_STATUS,) = (spec.template for spec in load_manual())


async def test_status_resolves_model_name_and_pins_facade_version(controller, executor):
    controller.respond('Client.FullStatus', {'model': {'name': 'prod'}})

    result = await executor.call(FULL_STATUS, {'model': 'prod'})

    assert result == {'model': {'name': 'prod'}}
    (call,) = controller.calls('Client.FullStatus')
    assert call['path'] == f'/model/{MODEL_UUID}/api'
    assert call['version'] == 8
    assert call['params'] == {'patterns': []}
    (login, _) = controller.calls('Admin.Login')
    assert login['version'] == 3
    assert login['params']['auth-tag'] == 'user-reader'
    assert login['params']['credentials'] == 's3cret'
    (lookup,) = controller.calls('ModelManager.ListModels')
    assert lookup['path'] == '/api'
    assert lookup['params'] == {'tag': 'user-reader'}


async def test_caller_arguments_are_passed_through(controller, executor):
    controller.respond('Client.FullStatus', {})
    await executor.call(
        FULL_STATUS, {'model': 'prod', 'patterns': ['mysql'], 'include-storage': True}
    )
    (call,) = controller.calls('Client.FullStatus')
    assert call['params'] == {'patterns': ['mysql'], 'include-storage': True}


async def test_model_uuid_is_cached_and_uuid_input_skips_lookup(controller, executor):
    controller.respond('Client.FullStatus', {})
    await executor.call(FULL_STATUS, {'model': 'admin/prod'})
    await executor.call(FULL_STATUS, {'model': 'admin/prod'})
    await executor.call(FULL_STATUS, {'model': f'ctrl:{MODEL_UUID}'})
    assert len(controller.calls('ModelManager.ListModels')) == 1
    assert len(controller.calls('Client.FullStatus')) == 3


async def test_facade_version_the_controller_lacks_is_refused_without_a_request(
    controller, executor
):
    controller.facades['Client'] = [6, 7]
    with pytest.raises(JujuError, match=r'Client\.FullStatus is not supported by this controller'):
        await executor.call(FULL_STATUS, {'model': 'prod'})
    assert not controller.calls('Client.FullStatus')


async def test_unsupported_series_is_refused(controller, executor):
    controller.server_version = '4.0.1'
    with pytest.raises(JujuError, match=r'not available for Juju 4\.0\.1; supported: 3\.6'):
        await executor.call(FULL_STATUS, {'model': 'prod'})
    assert not controller.calls('Client.FullStatus')


async def test_rpc_error_carries_juju_text_and_code(controller, executor):
    controller.respond('Client.FullStatus', error='permission denied')
    with pytest.raises(JujuError, match='permission denied') as raised:
        await executor.call(FULL_STATUS, {'model': 'prod'})
    assert raised.value.code == 'not found'


async def test_unknown_model_lists_visible_models(executor):
    with pytest.raises(JujuError, match=r"model 'staging' not found.*admin/prod"):
        await executor.call(FULL_STATUS, {'model': 'staging'})


async def test_model_argument_is_required(executor):
    with pytest.raises(JujuError, match='"model" argument is required'):
        await executor.call(FULL_STATUS, {})


async def test_unreachable_controller_reports_every_endpoint():
    executor = JujuExecutor(
        JujuConfig(endpoints=('127.0.0.1:1',), username='u', password='p', tls=False, timeout=2)
    )
    with pytest.raises(JujuError, match=r'cannot connect.*127\.0\.0\.1:1'):
        await executor.call(FULL_STATUS, {'model': 'prod'})


async def test_call_text_returns_errors_as_text(controller, config):
    tools = JujuTools(config)
    controller.respond('Client.FullStatus', {'model': {'name': 'prod'}})
    assert await tools.call_text('client.full_status', {'model': 'prod'}) == (
        '{"model":{"name":"prod"}}'
    )
    assert await tools.call_text('client.full_status', {'model': 'nope'}) == (
        "Error: model 'nope' not found; models visible to this user: admin/prod"
    )
    assert await tools.call_text('application.deploy', {}) == (
        "Error: unknown operation 'application.deploy'; available: client.full_status"
    )


def test_config_from_env(tmp_path):
    ca = tmp_path / 'ca.pem'
    ca.write_text('PEM')
    config = JujuConfig.from_env(
        {
            'UTCP_JUJU_ENDPOINT': '10.0.0.1:17070, 10.0.0.2:17070',
            'UTCP_JUJU_USERNAME': 'reader',
            'UTCP_JUJU_PASSWORD': 'pw',
            'UTCP_JUJU_CA_CERT_FILE': str(ca),
        }
    )
    assert config.endpoints == ('10.0.0.1:17070', '10.0.0.2:17070')
    assert config.user_tag == 'user-reader'
    assert config.ca_cert == 'PEM'
    with pytest.raises(JujuError, match='UTCP_JUJU_PASSWORD'):
        JujuConfig.from_env({'UTCP_JUJU_ENDPOINT': 'h:1', 'UTCP_JUJU_USERNAME': 'u'})

"""Fixtures for tests against a real Juju controller.

The `juju` fixture comes from pytest-jubilant: a temporary model on the current controller.
Jubilant drives the `juju` CLI for setup only (deploying, creating the read-only user); the
code under test talks to the controller over its websocket API.
"""

import json
import os
import secrets
from dataclasses import dataclass

import jubilant
import pytest

from utcp_juju import JujuConfig, JujuTools

DEPLOY_TIMEOUT = 20 * 60
# Any machine charm that reaches active on its own will do. The tests expect an LXD (or
# other machine) controller; Kubernetes models are not covered.
DEFAULT_CHARM = 'ubuntu'


@dataclass(frozen=True)
class Controller:
    """How to reach the controller the temporary model lives on."""

    name: str
    endpoints: tuple[str, ...]
    ca_cert: str


@dataclass(frozen=True)
class Deployment:
    """The temporary model and the one application deployed in it."""

    model: str
    app: str


def _split_model(juju: jubilant.Juju) -> tuple[str, str]:
    """Return (controller, model); controller is empty for the current one."""
    assert juju.model is not None
    controller, _, model = juju.model.rpartition(':')
    return controller, model


def _controller_args(juju: jubilant.Juju) -> tuple[str, ...]:
    controller, _ = _split_model(juju)
    return ('--controller', controller) if controller else ()


@pytest.fixture(scope='module')
def controller(juju: jubilant.Juju) -> Controller:
    name, _ = _split_model(juju)
    shown = json.loads(
        juju.cli('show-controller', *([name] if name else []), '--format', 'json',
                 include_model=False)
    )  # fmt: skip
    ((name, info),) = shown.items()
    details = info['details']
    return Controller(name, tuple(details['api-endpoints']), details['ca-cert'])


@pytest.fixture(scope='module')
def deployment(juju: jubilant.Juju) -> Deployment:
    """Deploy one small charm and wait for it to settle."""
    _, model = _split_model(juju)
    charm = os.environ.get('UTCP_JUJU_TEST_CHARM', DEFAULT_CHARM)
    app = 'app'
    juju.deploy(charm, app)
    juju.wait(lambda status: jubilant.all_active(status, app), timeout=DEPLOY_TIMEOUT)
    return Deployment(model, app)


@pytest.fixture(scope='module')
def reader_config(juju: jubilant.Juju, controller: Controller, deployment: Deployment):
    """A dedicated Juju user granted only `read` on the temporary model."""
    username = f'utcp-ro-{secrets.token_hex(3)}'
    password = secrets.token_urlsafe(16)
    scope = _controller_args(juju)
    juju.cli('add-user', username, *scope, include_model=False)
    try:
        juju.cli('change-user-password', username, '--no-prompt', *scope,
                 include_model=False, stdin=f'{password}\n')  # fmt: skip
        juju.cli('grant', username, 'read', deployment.model, *scope, include_model=False)
        yield JujuConfig(
            endpoints=controller.endpoints,
            username=username,
            password=password,
            ca_cert=controller.ca_cert,
        )
    finally:
        juju.cli('remove-user', username, '--yes', *scope, include_model=False)


@pytest.fixture
def tools(reader_config: JujuConfig) -> JujuTools:
    return JujuTools(reader_config)

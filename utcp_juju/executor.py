"""Executes ``juju`` call templates: one RPC request against one model."""

import re
from typing import Any

from utcp_juju.call_template import JujuCallTemplate
from utcp_juju.config import JujuConfig
from utcp_juju.connection import JujuConnection
from utcp_juju.errors import JujuError

# ModelManager versions whose ListModels this plugin knows; used for name lookups only.
_MODEL_MANAGER_VERSIONS = (10, 9)
_UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


class JujuExecutor:
    """Stateless per call: connect, log in, send one request, disconnect.

    Nothing about a model is cached except the name to UUID mapping.
    """

    def __init__(self, config: JujuConfig | None = None) -> None:
        self._config = config
        self._model_uuids: dict[str, str] = {}

    @property
    def config(self) -> JujuConfig:
        """The connection settings, read from the environment on first use."""
        if self._config is None:
            self._config = JujuConfig.from_env()
        return self._config

    async def call(self, template: JujuCallTemplate, args: dict[str, Any] | None) -> Any:
        """Run the tool described by ``template`` with the caller's ``args``."""
        if not template.facade or not template.method:
            raise JujuError('call template names no facade method')
        params = {**template.default_params, **(args or {})}
        model = params.pop('model', None)
        if not model:
            raise JujuError('the "model" argument is required')
        model_uuid = await self.resolve_model(model)
        # A connection per call costs a TLS handshake and a login, which also writes the
        # user's last-login time on the controller. If that adds up, replace it with a
        # singleton connection pool keyed by model UUID (idle timeout, reconnect on close,
        # requests matched by request-id so calls can share a connection).
        async with await JujuConnection.open(self.config, model_uuid) as connection:
            version = self._facade_version(template, connection)
            return await connection.request(template.facade, version, template.method, params)

    async def resolve_model(self, model: str) -> str:
        """Return the UUID for a model name, ``owner/name`` or UUID.

        A ``controller:`` prefix is accepted and ignored: one config is one controller.
        """
        name = model.split(':', 1)[1] if ':' in model else model
        if _UUID.match(name):
            return name
        if name in self._model_uuids:
            return self._model_uuids[name]
        async with await JujuConnection.open(self.config) as controller:
            models = await self._list_models(controller)
        matches = [uuid for candidates, uuid in models if name in candidates]
        if not matches:
            known = ', '.join(sorted(qualified for (_, qualified), _ in models)) or 'none'
            raise JujuError(f'model {model!r} not found; models visible to this user: {known}')
        if len(matches) > 1:
            raise JujuError(f'model name {model!r} is ambiguous; use owner/name')
        self._model_uuids[name] = matches[0]
        return matches[0]

    @staticmethod
    async def _list_models(connection: JujuConnection) -> list[tuple[tuple[str, str], str]]:
        """Return ((name, owner/name), uuid) for each model the login user can see."""
        served = connection.facades.get('ModelManager', [])
        version = next((v for v in _MODEL_MANAGER_VERSIONS if v in served), None)
        if version is None:
            raise JujuError('this endpoint does not serve a supported ModelManager version')
        result = await connection.request(
            'ModelManager', version, 'ListModels', {'tag': connection.user_tag}
        )
        models = []
        for entry in result.get('user-models') or []:
            info = entry.get('model') or {}
            owner = info.get('owner-tag', '').removeprefix('user-')
            models.append(
                ((info.get('name', ''), f'{owner}/{info.get("name", "")}'), info['uuid'])
            )
        return models

    @staticmethod
    def _facade_version(template: JujuCallTemplate, connection: JujuConnection) -> int:
        """Pick the facade version for this server. No negotiation, no downgrade."""
        server = connection.server_version
        series = '.'.join(server.split('.')[:2])
        version = template.versions.get(series)
        name = f'{template.facade}.{template.method}'
        if version is None:
            supported = ', '.join(sorted(template.versions)) or 'none'
            raise JujuError(f'{name} is not available for Juju {server}; supported: {supported}')
        if version not in connection.facades.get(template.facade or '', []):
            raise JujuError(f'{name} is not supported by this controller (Juju {server})')
        return version

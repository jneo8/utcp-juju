"""One authenticated websocket connection to a Juju API endpoint."""

import asyncio
import ssl
from typing import Any

import orjson
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from utcp_juju.config import JujuConfig
from utcp_juju.errors import JujuError

# The name every controller certificate carries; the juju client verifies against it too.
_SERVER_NAME = 'juju-apiserver'


def _ssl_context(config: JujuConfig) -> ssl.SSLContext | None:
    if not config.tls:
        return None
    if config.ca_cert:
        return ssl.create_default_context(cadata=config.ca_cert)
    return ssl.create_default_context()


async def _open_socket(config: JujuConfig, path: str) -> ClientConnection:
    """Connect to ``path`` on the first endpoint that answers."""
    context = _ssl_context(config)
    kwargs: dict[str, Any] = {
        'max_size': config.max_frame_bytes,
        'open_timeout': config.timeout,
    }
    if context is not None:
        kwargs['ssl'] = context
        if config.ca_cert:
            kwargs['server_hostname'] = _SERVER_NAME
    scheme = 'wss' if config.tls else 'ws'
    failures = []
    for endpoint in config.endpoints:
        try:
            return await connect(f'{scheme}://{endpoint}{path}', **kwargs)
        except (OSError, TimeoutError, WebSocketException) as exc:
            failures.append(f'{endpoint}: {exc}')
    raise JujuError('cannot connect to the Juju controller: ' + '; '.join(failures))


class JujuConnection:
    """A logged-in RPC connection. Use as an async context manager; one request at a time."""

    def __init__(self, config: JujuConfig, socket: ClientConnection) -> None:
        self._config = config
        self._socket = socket
        self._request_id = 0
        self.facades: dict[str, list[int]] = {}
        self.server_version = ''
        self.user_tag = config.user_tag

    @classmethod
    async def open(cls, config: JujuConfig, model_uuid: str | None = None) -> 'JujuConnection':
        """Connect to the controller endpoint, or a model's when ``model_uuid`` is given."""
        path = f'/model/{model_uuid}/api' if model_uuid else '/api'
        connection = cls(config, await _open_socket(config, path))
        try:
            await connection._login()
        except BaseException:
            await connection.close()
            raise
        return connection

    async def __aenter__(self) -> 'JujuConnection':
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the websocket."""
        await self._socket.close()

    async def _login(self) -> None:
        response = await self.request(
            'Admin',
            3,
            'Login',
            {
                'auth-tag': self._config.user_tag,
                'credentials': self._config.password,
                'nonce': '',
                'client-version': self._config.client_version,
            },
        )
        self.facades = {
            facade['name']: list(facade.get('versions') or [])
            for facade in response.get('facades') or []
        }
        self.server_version = response.get('server-version', '')
        identity = (response.get('user-info') or {}).get('identity')
        if identity:
            self.user_tag = identity

    async def request(self, facade: str, version: int, method: str, params: dict[str, Any]) -> Any:
        """Send one RPC request and return its ``response``; raise on an ``error``."""
        self._request_id += 1
        request_id = self._request_id
        message = {
            'request-id': request_id,
            'type': facade,
            'version': version,
            'request': method,
            'params': params,
        }
        try:
            async with asyncio.timeout(self._config.timeout):
                await self._socket.send(orjson.dumps(message).decode())
                while True:
                    reply = orjson.loads(await self._socket.recv())
                    if reply.get('request-id') == request_id:
                        break
        except TimeoutError:
            raise JujuError(f'{facade}.{method} timed out after {self._config.timeout}s') from None
        except ConnectionClosed as exc:
            raise JujuError(f'connection closed during {facade}.{method}: {exc}') from None
        if reply.get('error'):
            raise JujuError(reply['error'], reply.get('error-code', ''))
        return reply.get('response', {})

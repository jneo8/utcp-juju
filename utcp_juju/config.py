"""Connection settings for a Juju controller."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from utcp_juju.errors import JujuError

DEFAULT_MAX_FRAME_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class JujuConfig:
    """Everything a login needs. No Juju client store is read.

    Attributes:
        endpoints: Controller API addresses (``host:17070``), tried in order.
        username: Local Juju user name (``user-`` tag prefix optional).
        password: That user's password.
        ca_cert: PEM CA certificate of the controller. When set, the server certificate is
            verified against it under the name ``juju-apiserver``, as the juju client does.
            When ``None``, the system trust store and the endpoint host name are used.
        client_version: Version reported at login; the controller rejects clients whose
            major version it does not support.
        max_frame_bytes: Websocket frame limit. A large model's FullStatus is several MB.
        timeout: Seconds allowed for connecting and for each request.
        tls: Set ``False`` only for tests against a plain ``ws://`` server.
    """

    endpoints: tuple[str, ...]
    username: str
    password: str
    ca_cert: str | None = None
    client_version: str = '3.6.0'
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES
    timeout: float = 60.0
    tls: bool = True

    @property
    def user_tag(self) -> str:
        """The login tag for ``username``."""
        name = self.username
        return name if name.startswith('user-') else f'user-{name}'

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> 'JujuConfig':
        """Build the config from ``UTCP_JUJU_*`` environment variables."""
        env = os.environ if env is None else env
        missing = [
            name
            for name in ('UTCP_JUJU_ENDPOINT', 'UTCP_JUJU_USERNAME', 'UTCP_JUJU_PASSWORD')
            if not env.get(name)
        ]
        if missing:
            raise JujuError(f'missing environment variable(s): {", ".join(missing)}')
        ca_cert = env.get('UTCP_JUJU_CA_CERT')
        ca_file = env.get('UTCP_JUJU_CA_CERT_FILE')
        if not ca_cert and ca_file:
            ca_cert = Path(ca_file).read_text()
        endpoints = tuple(e.strip() for e in env['UTCP_JUJU_ENDPOINT'].split(',') if e.strip())
        return cls(
            endpoints=endpoints,
            username=env['UTCP_JUJU_USERNAME'],
            password=env['UTCP_JUJU_PASSWORD'],
            ca_cert=ca_cert or None,
        )

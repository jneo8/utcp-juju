import json
from urllib.parse import urlsplit

import pytest
from websockets.asyncio.server import serve

from utcp_juju import JujuConfig, JujuExecutor

MODEL_UUID = '11111111-2222-3333-4444-555555555555'
FACADES = {'Admin': [3], 'Client': [6, 7, 8], 'ModelManager': [9, 10]}


class FakeController:
    """A websocket server that replays canned Juju responses and records what it was sent."""

    def __init__(self):
        self.server_version = '3.6.12'
        self.facades = {name: list(versions) for name, versions in FACADES.items()}
        self.responses = {}
        self.requests = []
        self.port = 0

    def respond(self, name, response=None, error=None):
        self.responses[name] = (response, error)

    def calls(self, name):
        return [r for r in self.requests if f'{r["type"]}.{r["request"]}' == name]

    async def handler(self, socket):
        url = urlsplit(socket.request.path)
        async for raw in socket:
            request = json.loads(raw) | {'path': url.path}
            self.requests.append(request)
            reply = {'request-id': request['request-id']}
            name = f'{request["type"]}.{request["request"]}'
            if name == 'Admin.Login':
                reply['response'] = {
                    'server-version': self.server_version,
                    'facades': [{'name': n, 'versions': v} for n, v in self.facades.items()],
                    'user-info': {'identity': request['params']['auth-tag']},
                }
            elif name == 'ModelManager.ListModels':
                reply['response'] = {
                    'user-models': [
                        {'model': {'name': 'prod', 'uuid': MODEL_UUID, 'owner-tag': 'user-admin'}}
                    ]
                }
            elif name in self.responses:
                response, error = self.responses[name]
                if error:
                    reply |= {'error': error, 'error-code': 'not found'}
                else:
                    reply['response'] = response
            else:
                reply['error'] = f'no such request - method {name} is not implemented'
            await socket.send(json.dumps(reply))


@pytest.fixture
async def controller():
    fake = FakeController()
    async with serve(fake.handler, '127.0.0.1', 0) as server:
        fake.port = server.sockets[0].getsockname()[1]
        yield fake


@pytest.fixture
def config(controller):
    return JujuConfig(
        endpoints=(f'127.0.0.1:{controller.port}',),
        username='reader',
        password='s3cret',
        tls=False,
        timeout=5,
    )


@pytest.fixture
def executor(config):
    return JujuExecutor(config)

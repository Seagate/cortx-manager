import sys
import pytest
import asyncio


from importlib import import_module
from aiohttp import web
from multiprocessing import Process


@pytest.fixture(scope='module')
def setup_redirection():
    sys.modules['csm'] = import_module('csm.src')


@pytest.fixture(scope='module')
def server():
    from csm.core.blogic import const

    def start_server():
        async def hello(request):
            print(555)
            return web.Response(text='response')

        app = web.Application()
        app.add_routes([web.get('/api/alerts', hello)])
        web.run_app(app,
                    host='localhost',
                    port=const.CSM_AGENT_PORT)

    p = Process(target=start_server)
    p.start()
    yield
    p.terminate()


@pytest.fixture(scope='module')
def scm_client():
    from csm.cli.csm_client import CsmRestClient
    from csm.core.blogic import const

    client = CsmRestClient(f"http://localhost:{const.CSM_AGENT_PORT}/api")
    return client


@pytest.fixture(scope='module')
def command():
    from csm.cli.command_factory import CommandFactory
    command = CommandFactory.get_command(['alerts', 'show'])

    return command


@pytest.fixture(scope='module')
def loop():
    loop = asyncio.get_event_loop()
    return loop

import sys
import pytest
import asyncio
import time


from importlib import import_module
from aiohttp import web
from multiprocessing import Process


@pytest.fixture(scope='module')
def imprt_redirection():
    sys.modules['csm'] = import_module('csm.src')


@pytest.fixture(scope='module')
def server():
    from csm.core.blogic import const

    def start_server():
        async def r_get(request):
            return web.Response(text='{"response":"show"}')

        async def r_patch(request):
            return web.Response(text='{"response":"acknowledge"}')

        app = web.Application()
        app.add_routes([web.get('/api/alerts', r_get),
                        web.patch('/api/alerts', r_patch
                                  )])
        web.run_app(app,
                    host='localhost',
                    port=const.CSM_AGENT_PORT)

    p = Process(target=start_server)
    p.start()

    # Wait for server to start.
    # Better to put in event loop instead of a separate process later.
    time.sleep(2)

    yield

    p.terminate()


@pytest.fixture(scope='module')
def csm_client():
    from csm.cli.csm_client import CsmRestClient
    from csm.core.blogic import const

    client = CsmRestClient(f"http://localhost:{const.CSM_AGENT_PORT}/api")
    return client


@pytest.fixture(scope='module')
def loop():
    loop = asyncio.get_event_loop()
    return loop

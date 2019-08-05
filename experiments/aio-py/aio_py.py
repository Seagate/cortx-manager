#!/usr/bin/env python3

import os
import json
import asyncio
from aiohttp import web, WSMsgType
from datetime import datetime
from weakref import WeakSet

BG_SLEEP_SECONDS = 15
STG_WS_CLIENTS = 'ws.clients'
STG_WS_BGTASK = 'ws.bgtask'

app = web.Application()

async def api_handler(request):
    print(f'api handler {request}')

    command = request.match_info.get('command', '@default')
    opt = request.match_info.get('opt', '')
    cwd = os.getcwd()
    rspobj = { 'status' : 'success', 'command' : command, 'opt': opt, 'cwd' : cwd }
    # return web.Response(text = json.dumps(rspobj))
    return web.json_response(rspobj)

async def static_handler(request):
    print(f'static handler {request}')

    base = './client'
    path = request.match_info.get('path', '.')
    realpath = os.path.abspath(f'{base}/{path}')
    if os.path.exists(realpath) and os.path.isdir(realpath):
        realpath = os.path.abspath(f'{realpath}/index.html')
    if os.path.exists(realpath):
        return web.FileResponse(realpath)
    return web.FileResponse(f'{base}/error.html')
    # rspobj = { 'status' : 'error', 'path' : realpath }
    # return web.Response(text = json.dumps(rspobj))

async def ws_background(app):
    print(f'background start {app}')
    try:
        while True:
            await asyncio.sleep(BG_SLEEP_SECONDS)

            ts = datetime.utcnow().isoformat()
            print(f'background [{ts}] {app}')
            await ws_broadcast(app, f'TIME: {ts}')

    except asyncio.CancelledError:
        print(f'background cancel {app}')

    print(f'background done {app}')

async def ws_startup(app):
    print(f'startup {app}')
    app[STG_WS_BGTASK] = app.loop.create_task(ws_background(app))
    app[STG_WS_CLIENTS] = WeakSet()

async def ws_shutdown(app):
    print(f'shutdown {app}')
    app[STG_WS_BGTASK].cancel()
    pass

async def ws_broadcast(app, msg):
    clients = app[STG_WS_CLIENTS].copy() # explicit copy because the list can change asynchronously
    try:
        for ws in clients:
            await ws.send_str(msg)
    except:
        print(f'broadcast error')

async def ws_handler(request):
    print(f'ws handler {request}')

    ws = web.WebSocketResponse()
    print(f'ws response {ws}')
    await ws.prepare(request)
    request.app[STG_WS_CLIENTS].add(ws)

    print(f'ws async message loop {ws}')
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    await ws_broadcast(app, f'{msg.data}/answer')
            elif msg.type == WSMsgType.ERROR:
                print(f'ws connection closed with exception {ws.exception()}')
    finally:
        request.app[STG_WS_CLIENTS].discard(ws)

    print(f'ws connection closed {ws}')
    return ws

app.add_routes(
    [web.get('/ws', ws_handler),
     web.get('/api/{command}/{opt}', api_handler),
     web.get('/api/{command}', api_handler),
     web.get('/{path:.*}', static_handler),
     ]
    );

app.on_startup.append(ws_startup)
app.on_shutdown.append(ws_shutdown)

web.run_app(app)

print(f'done {app}')

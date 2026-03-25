#!/usr/bin/env python
# coding: utf-8

import os
import asyncio

from aiohttp import web


LOG_PATH = os.environ.get("LOG_PATH", "/opt/ripple/log/debug.log")
PORT = int(os.environ.get("PORT", "9999"))


async def tail_log(ws: web.WebSocketResponse, raddress: str):
    while not os.path.exists(LOG_PATH):
        if ws.closed:
            return
        await asyncio.sleep(0.5)

    pos = os.path.getsize(LOG_PATH)

    while not ws.closed:
        try:
            size = os.path.getsize(LOG_PATH)
        except FileNotFoundError:
            await asyncio.sleep(0.5)
            continue

        # Handle file rotation
        if size < pos:
            pos = 0

        if size > pos:
            with open(LOG_PATH, "r", errors="replace") as f:
                f.seek(pos)
                for line in f:
                    if raddress in line:
                        try:
                            await ws.send_str(line.rstrip("\n"))
                        except ConnectionResetError:
                            return
                pos = f.tell()

        await asyncio.sleep(0.1)


async def handle_debugstream(request: web.Request) -> web.WebSocketResponse:
    raddress = request.match_info["raddress"]
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    task = asyncio.create_task(tail_log(ws, raddress))
    try:
        async for _ in ws:
            pass
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/debugstream/{raddress}", handle_debugstream)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), port=PORT)

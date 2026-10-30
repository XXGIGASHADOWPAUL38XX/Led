"""Run the headless processing API: python -m backend.api.server --port 8000."""
import argparse
import asyncio
from contextlib import suppress
import logging
import re
import time

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from .handlers import Handlers
from .protocol import MAX_BYTES, decode, encode, event
from .router import Router

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, socket):
        self.socket = socket
        self.outbox = asyncio.Queue(maxsize=128)
        self.subscriptions = ()
        self.in_flight = None
        self.sequence = 0
        self.jobs = set()
        self.search_results = {}

    async def send(self, message):
        # Never grow an unbounded reliable queue for an unresponsive client.
        try:
            self.outbox.put_nowait(encode(message))
        except asyncio.QueueFull:
            await self.socket.close(code=1013, reason="Client is too slow; reconnect for a snapshot")

    async def write(self):
        while True:
            await self.socket.send(await self.outbox.get())


class Server:
    def __init__(self, runtime):
        self.runtime = runtime
        self.sessions = set()
        self.handlers = Handlers(runtime, self.broadcast)
        self.router = Router(self.handlers)

    async def broadcast(self, message):
        if self.sessions:
            await asyncio.gather(*(session.send(message) for session in tuple(self.sessions)))

    async def connect(self, socket):
        if socket.request.path != "/ws":
            await socket.close(code=1008, reason="Use /ws")
            return
        session = Session(socket)
        self.sessions.add(session)
        writer = asyncio.create_task(session.write())
        try:
            await session.send(event("graph.snapshot", self.runtime.snapshot(), self.runtime.revision))
            await session.send(event("history.update", {"canUndo": bool(self.router.history.entries)}, self.runtime.revision))
            async for packet in socket:
                try:
                    message = decode(packet)
                    if message["type"] == "player.search":
                        # Network searches must not block control messages or frame ACKs.
                        job = asyncio.create_task(self.router.dispatch(session, message))
                        session.jobs.add(job)
                        job.add_done_callback(session.jobs.discard)
                    else:
                        await self.router.dispatch(session, message)
                except (ValueError, TypeError, KeyError) as error:
                    await session.send(event("error", {"message": str(error)}, self.runtime.revision))
        except ConnectionClosed:
            pass
        finally:
            self.sessions.discard(session)
            for job in session.jobs:
                job.cancel()
            if session.jobs:
                await asyncio.gather(*session.jobs, return_exceptions=True)
            writer.cancel()
            with suppress(asyncio.CancelledError, ConnectionClosed):
                await writer

    async def processing(self):
        next_frame = time.monotonic()
        while True:
            for error in self.runtime.tick():
                await self.broadcast(event("error", {**error, "processing": True}, self.runtime.revision))
            for update in self.runtime.setting_updates():
                await self.broadcast(event("state.update", update, self.runtime.revision))
            now = time.monotonic()
            if now >= next_frame:
                next_frame = now + 0.05
                for update in self.runtime.schema_updates():
                    await self.broadcast(event("state.update", update, self.runtime.revision))
                players = [self.handlers.player_state(node) for node in self.runtime.players.values()]
                for session in tuple(self.sessions):
                    if session.in_flight is not None:
                        continue
                    if not session.subscriptions and not players:
                        continue
                    session.sequence += 1
                    session.in_flight = session.sequence
                    await session.send(event("frame", {"sequence": session.sequence,
                        "values": self.runtime.frame(session.subscriptions), "players": players}, self.runtime.revision))
            await asyncio.sleep(0.005)

    async def run(self, host="127.0.0.1", port=8000):
        # Compression trades CPU for bandwidth; packed numeric frames stay raw.
        async with serve(self.connect, host, port, max_size=MAX_BYTES, max_queue=16, compression=None,
                         origins=[None, re.compile(r"http://(localhost|127\.0\.0\.1)(:\d+)?")]):
            logger.info("Listening on ws://%s:%s/ws", host, port)
            try:
                await self.processing()
            finally:
                self.runtime.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    from .runtime import Runtime
    logging.basicConfig(level=logging.INFO)
    runtime = Runtime()
    runtime.load({"nodes": [
        {"id": "buffer-1", "type": "Buffer", "position": [0, 0], "parameters": {"length": 2048}},
        {"id": "amplitudes-1", "type": "Amplitudes", "position": [0, 0], "parameters": {}},
    ], "connections": [{"id": "buffer-amplitudes", "source": {"nodeId": "buffer-1", "element": "data"},
                        "target": {"nodeId": "amplitudes-1", "element": "buffer"}}]})
    try:
        asyncio.run(Server(runtime).run(port=args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

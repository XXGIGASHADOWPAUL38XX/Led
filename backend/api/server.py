"""Run the headless processing API: python -m backend.api.server --port 8000."""
import argparse
import asyncio
from contextlib import asynccontextmanager, suppress
import logging
import re
import time

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .catalog import Catalog
from .handlers import Handlers
from .openapi import document
from .protocol import MAX_BYTES, decode, encode, event
from .rest import routes
from .router import Router
from .schemas import CatalogNode, Model

logger = logging.getLogger(__name__)
# Only the local frontend (any port) or non-browser clients may drive the lights.
LOCAL_ORIGIN = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
# Compression trades CPU for bandwidth; packed numeric frames stay raw.
# The WebSocket carries what must stay live; everything else is an HTTP resource (backend/api/rest.py).
WEBSOCKET_COMMANDS = {"element.set", "streams.update", "frame.ack"}
uvicorn_options = {"ws_max_size": MAX_BYTES, "ws_max_queue": 16, "ws_per_message_deflate": False}


class Session:
    def __init__(self, socket):
        self.socket = socket
        self.outbox = asyncio.Queue(maxsize=128)
        self.subscriptions = set()
        self.in_flight = None
        self.sequence = 0

    async def send(self, message):
        # Never grow an unbounded reliable queue for an unresponsive client.
        try:
            self.outbox.put_nowait(encode(message))
        except asyncio.QueueFull:
            await self.socket.close(code=1013, reason="Client is too slow; reconnect for a snapshot")

    async def write(self):
        while True:
            await self.socket.send_bytes(await self.outbox.get())


class Server:
    def __init__(self, runtime):
        self.runtime = runtime
        self.sessions = set()
        self.catalog = Catalog(runtime.catalog.classes)
        self.handlers = Handlers(runtime, self.broadcast)
        self.router = Router(self.handlers)

    async def broadcast(self, message):
        if self.sessions:
            await asyncio.gather(*(session.send(message) for session in tuple(self.sessions)))

    async def connect(self, socket: WebSocket):
        origin = socket.headers.get("origin")
        if origin is not None and not re.fullmatch(LOCAL_ORIGIN, origin):
            await socket.close(code=1008, reason="Origin not allowed")
            return
        await socket.accept()
        session = Session(socket)
        self.sessions.add(session)
        writer = asyncio.create_task(session.write())
        try:
            await self.greet(session)
            while (packet := await socket.receive())["type"] != "websocket.disconnect":
                await self.receive(session, packet)
            logger.info("WebSocket closed: peer=%s code=%s reason=%s", socket.client, packet.get("code"), packet.get("reason"))
        except WebSocketDisconnect as error:
            logger.warning("WebSocket disconnected: peer=%s code=%s reason=%s", socket.client, error.code, error.reason)
        finally:
            self.sessions.discard(session)
            writer.cancel()
            with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                await writer

    async def greet(self, session):
        """A new session starts from the current state; commands are never replayed."""
        await session.send(event("graph.snapshot", self.runtime.snapshot(), self.runtime.revision))
        await session.send(event("history.update", {"canUndo": bool(self.router.history.entries)}, self.runtime.revision))
        await session.send(event("jev.update", self.router.generation.state, self.runtime.revision))
        if self.router.generation.preview is not None:
            await session.send(event("jev.preview", self.router.generation.preview, self.runtime.revision))

    async def receive(self, session, packet):
        request_id = None
        try:
            message = decode(packet.get("bytes"))
            request_id = message.get("requestId")
            if message["type"] not in WEBSOCKET_COMMANDS:
                raise ValueError(f"{message['type']} is served by the HTTP API")
            await self.router.dispatch(session, message)
        except (ValueError, TypeError, KeyError) as error:
            await session.send(event("error", {"message": str(error)}, self.runtime.revision, request_id))

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
                await self.send_frames()
            await asyncio.sleep(0.005)

    async def send_frames(self):
        """One frame per session in flight at most: a slow client skips frames instead of queueing them."""
        players = [self.handlers.player_state(node) for node in self.runtime.players.values()]
        for session in tuple(self.sessions):
            if session.in_flight is not None or not (session.subscriptions or players):
                continue
            session.sequence += 1
            session.in_flight = session.sequence
            await session.send(event("frame", {"sequence": session.sequence,
                "values": self.runtime.frame(session.subscriptions), "players": players}, self.runtime.revision))



class Health(Model):
    status: str
    revision: int


def create_app(server):
    @asynccontextmanager
    async def lifespan(app):
        processing = asyncio.create_task(server.processing())
        try:
            yield
        finally:
            processing.cancel()
            with suppress(asyncio.CancelledError):
                await processing
            await server.router.generation.cancel()
            server.runtime.close()

    app = FastAPI(title="LED backend", version="1", lifespan=lifespan, generate_unique_id_function=lambda route: route.name)
    app.add_middleware(CORSMiddleware, allow_origin_regex=LOCAL_ORIGIN, allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["X-Revision"])

    @app.get("/api/v1/health")
    async def health() -> Health:
        return Health(status="ok", revision=server.runtime.revision)

    @app.get("/api/v1/catalog", response_model=list[CatalogNode], response_model_exclude_none=True)
    async def catalog(request: Request):
        # The catalog only changes with the backend code: clients revalidate and usually get a bodiless 304.
        headers = {"ETag": server.catalog.etag, "Cache-Control": "no-cache"}
        if request.headers.get("if-none-match") == server.catalog.etag:
            return Response(status_code=304, headers=headers)
        return Response(server.catalog.body, media_type="application/json", headers=headers)

    app.include_router(routes(server))

    @app.websocket("/ws")
    async def stream(socket: WebSocket):
        await server.connect(socket)

    app.openapi = lambda: document(app)
    return app


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
    uvicorn.run(create_app(Server(runtime)), host="127.0.0.1", port=args.port, **uvicorn_options)


if __name__ == "__main__":
    main()

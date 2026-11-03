"""Explicit routing: message names map to ordinary handler methods."""
import logging
import asyncio

from .protocol import event
from .history import History
from .generation import Generation
from .schemas import parse_command


# Commands refused for a reason the client can fix; anything else is a backend bug and is logged.
REFUSALS = (ValueError, TypeError, KeyError, IndexError, OverflowError)


class Router:
    def __init__(self, handlers):
        self.handlers = handlers
        self.history = History(handlers.runtime)
        self.edit_lock = asyncio.Lock()
        self.generation = Generation(self)
        self.routes = {
            "graph.copy": handlers.graph_copy, "graph.paste": handlers.graph_paste,
            "jev.generate": self.generation.start, "jev.cancel": self.generation.cancel,
            "graph.get": handlers.graph_get, "graph.load": handlers.graph_load, "graph.move": handlers.graph_move,
            "graph.restore": handlers.graph_restore, "node.describe": handlers.node_describe,
            "node.add": handlers.node_add, "node.remove": handlers.node_remove, "node.move": handlers.node_move,
            "node.configure": handlers.node_configure, "node.start": handlers.node_start, "node.stop": handlers.node_stop,
            "connection.add": handlers.connection_add, "connection.remove": handlers.connection_remove,
            "element.set": handlers.element_set, "streams.update": handlers.streams_update, "frame.ack": handlers.frame_ack,
            "player.play": handlers.player_play, "player.pause": handlers.player_pause,
            "player.seek": handlers.player_seek, "player.search": handlers.player_search,
            "playlist.add": handlers.playlist_add, "playlist.remove": handlers.playlist_remove,
        }

    async def execute(self, origin, kind, payload):
        """Validate and run one command for `origin` (a WebSocket session or an HTTP client id); raises on refusal."""
        payload = parse_command(kind, payload)
        if kind not in History.commands and kind != "graph.undo":
            return await self.routes[kind](origin, payload)
        async with self.edit_lock:
            if kind == "graph.undo":
                route, inverse = self.history.peek()
                result = await self.routes[route](origin, inverse)
                self.history.entries.pop()
            else:
                inverse = self.history.capture(kind, payload) if payload["recordHistory"] else None
                result = await self.routes[kind](origin, payload)
                if inverse is not None:
                    self.history.record(inverse, origin, kind, payload)
            await self.handlers.broadcast(event("history.update", {"canUndo": bool(self.history.entries)}, self.handlers.runtime.revision))
        return result

    async def dispatch(self, session, message):
        request_id = message.get("requestId")
        try:
            kind = message["type"]
            result = await self.execute(session, kind, message.get("payload", {}))
            if kind != "frame.ack":
                await session.send(event("ack", {"command": kind, "result": result}, self.handlers.runtime.revision, request_id))
        except REFUSALS as error:
            await session.send(event("error", {"message": str(error)}, self.handlers.runtime.revision, request_id))
        except Exception:
            logging.getLogger(__name__).exception("Command failed: %s", message["type"])
            await session.send(event("error", {"message": "Command failed; see backend logs"}, self.handlers.runtime.revision, request_id))

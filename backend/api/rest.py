"""HTTP resources for graph editing; each route runs the same validated command as its WebSocket twin."""
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .protocol import from_json, to_json
from .router import REFUSALS
from .schemas import (Command, Connection, ConnectionAdd, Finite, GenerationState, Graph, GraphLoad, GraphMove, GraphPaste,
                      GraphState, JevGenerate, Model, NodeAdd, NodeDescriptor, NodeIds, PlayerResults, PlayerState)


class Revision(Model):
    revision: int


class NodeCreated(Model):
    nodeId: str


class Copied(Model):
    graph: Graph


class Pasted(Model):
    nodeIds: list[str]


class NodeParameters(Command):
    parameters: dict[str, Any]


class TrackChoice(Command):
    trackId: str | None = None


class Track(Command):
    trackId: str


class Seek(Command):
    position: Finite


class Loading(Model):
    loading: bool


def routes(server):
    api = APIRouter(prefix="/api/v1")

    async def command(request: Request, kind, payload=None, status_code=200):
        """Run a command for this browser tab; X-History-Group makes one gesture undo as one step."""
        group = request.headers.get("x-history-group")
        payload = {**from_json(payload or {}), **({"historyGroup": int(group)} if group else {})}
        origin = request.headers.get("x-client-id", request.client.host)
        try:
            result = await server.router.execute(origin, kind, payload)
        except REFUSALS as error:
            return JSONResponse({"detail": str(error)}, status_code=422)
        # The revision this command produced: clients wait for it on the WebSocket before trusting the result.
        return JSONResponse(to_json(result), status_code=status_code,
                            headers={"X-Revision": str(server.runtime.revision)})

    @api.get("/graph", response_model=GraphState)
    async def get_graph():
        return JSONResponse(to_json({**server.runtime.snapshot(), "revision": server.runtime.revision}))

    @api.put("/graph", response_model=Revision)
    async def load_graph(request: Request, body: GraphLoad):
        return await command(request, "graph.load", body.model_dump(by_alias=True))

    @api.post("/graph/undo")
    async def undo(request: Request) -> Any:
        return await command(request, "graph.undo")

    @api.post("/graph/copy", response_model=Copied)
    async def copy_nodes(request: Request, body: NodeIds):
        return await command(request, "graph.copy", body.model_dump())

    @api.post("/graph/paste", response_model=Pasted)
    async def paste_nodes(request: Request, body: GraphPaste):
        return await command(request, "graph.paste", body.model_dump())

    @api.patch("/graph/positions")
    async def move_nodes(request: Request, body: GraphMove) -> Any:
        return await command(request, "graph.move", body.model_dump())

    @api.get("/node-types/{nodeType}", response_model=NodeDescriptor)
    async def describe_node_type(request: Request, nodeType: str):
        return await command(request, "node.describe", {"nodeType": nodeType})

    @api.post("/nodes", response_model=NodeCreated)
    async def add_node(request: Request, body: NodeAdd):
        return await command(request, "node.add", body.model_dump())

    @api.delete("/nodes/{nodeId}", response_model=Revision)
    async def remove_node(request: Request, nodeId: str):
        return await command(request, "node.remove", {"nodeId": nodeId})

    @api.put("/nodes/{nodeId}/parameters", response_model=Revision)
    async def configure_node(request: Request, nodeId: str, body: NodeParameters):
        return await command(request, "node.configure", {**body.model_dump(), "nodeId": nodeId})

    @api.post("/nodes/{nodeId}/start")
    async def start_node(request: Request, nodeId: str) -> None:
        return await command(request, "node.start", {"nodeId": nodeId})

    @api.post("/nodes/{nodeId}/stop")
    async def stop_node(request: Request, nodeId: str) -> None:
        return await command(request, "node.stop", {"nodeId": nodeId})

    @api.post("/connections", response_model=Connection)
    async def add_connection(request: Request, body: ConnectionAdd):
        return await command(request, "connection.add", body.model_dump())

    @api.delete("/connections/{connectionId}", response_model=Revision)
    async def remove_connection(request: Request, connectionId: str):
        return await command(request, "connection.remove", {"connectionId": connectionId})

    @api.post("/players/{nodeId}/play", response_model=PlayerState | Loading)
    async def play(request: Request, nodeId: str, body: TrackChoice):
        return await command(request, "player.play", {**body.model_dump(exclude_unset=True), "nodeId": nodeId})

    @api.post("/players/{nodeId}/pause", response_model=PlayerState)
    async def pause(request: Request, nodeId: str):
        return await command(request, "player.pause", {"nodeId": nodeId})

    @api.post("/players/{nodeId}/seek", response_model=PlayerState)
    async def seek(request: Request, nodeId: str, body: Seek):
        return await command(request, "player.seek", {"position": body.position, "nodeId": nodeId})

    @api.get("/players/{nodeId}/search", response_model=PlayerResults)
    async def search(request: Request, nodeId: str, query: str):
        return await command(request, "player.search", {"nodeId": nodeId, "query": query})

    @api.post("/players/{nodeId}/playlist", response_model=Loading)
    async def queue_track(request: Request, nodeId: str, body: Track):
        return await command(request, "playlist.add", {"trackId": body.trackId, "nodeId": nodeId})

    @api.delete("/players/{nodeId}/playlist", response_model=PlayerState)
    async def unqueue_track(request: Request, nodeId: str, trackId: str):
        return await command(request, "playlist.remove", {"trackId": trackId, "nodeId": nodeId})

    @api.post("/generations", response_model=GenerationState, status_code=202)
    async def generate(request: Request, body: JevGenerate):
        # Accepted, not done: progress, the preview and the result arrive as jev.* WebSocket events.
        return await command(request, "jev.generate", body.model_dump(), status_code=202)

    @api.delete("/generations/current", response_model=GenerationState)
    async def cancel_generation(request: Request):
        return await command(request, "jev.cancel")

    return api

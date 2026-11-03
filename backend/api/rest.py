"""HTTP resources for graph editing; each route runs the same validated command as its WebSocket twin."""
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .protocol import from_json, to_json
from .router import REFUSALS
from .schemas import (Command, Connection, ConnectionAdd, Graph, GraphLoad, GraphMove, GraphPaste, GraphState, Model,
                      NodeAdd, NodeDescriptor, NodeIds)


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


def routes(server):
    api = APIRouter(prefix="/api/v1")

    async def command(request: Request, kind, payload=None):
        """Run a command for this browser tab; X-History-Group makes one gesture undo as one step."""
        group = request.headers.get("x-history-group")
        payload = {**from_json(payload or {}), **({"historyGroup": int(group)} if group else {})}
        origin = request.headers.get("x-client-id", request.client.host)
        try:
            result = await server.router.execute(origin, kind, payload)
        except REFUSALS as error:
            return JSONResponse({"detail": str(error)}, status_code=422)
        # The revision this command produced: clients wait for it on the WebSocket before trusting the result.
        return JSONResponse(to_json(result), headers={"X-Revision": str(server.runtime.revision)})

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

    return api

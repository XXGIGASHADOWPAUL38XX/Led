"""Wire contract: every command payload and server event, shared with the generated TypeScript types.

Field names are the wire names (camelCase), so the Python models, the MessagePack payloads and the
TypeScript types spell them identically. Values that carry packed NumPy arrays stay `Any`.
"""
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Finite = Annotated[float, Field(allow_inf_nan=False)]
Position = Annotated[list[Finite], Field(min_length=2, max_length=2)]


class Model(BaseModel):
    """Fields typed `T = None` are omitted when they do not apply and never sent as null; `T | None` may be null."""
    model_config = ConfigDict(extra="forbid")


# --- Graph -----------------------------------------------------------------------------------------

class Endpoint(Model):
    nodeId: str
    element: str


class GraphNode(Model):
    # The runtime fills position and parameters on every node it holds, so responses always carry them.
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)
    id: str
    type: str
    position: Position = [0, 0]
    parameters: dict[str, Any] = {}


class Connection(Model):
    id: str
    source: Endpoint
    target: Endpoint


class Graph(Model):
    nodes: list[GraphNode]
    connections: list[Connection]


class LegacyTemplate(BaseModel):
    """Jev's saved constructor values: nodes with `state` and `connects` tuples."""
    nodes: list[dict[str, Any]]
    connects: list[Annotated[list[str], Field(min_length=4, max_length=4)]]


# --- Descriptors -----------------------------------------------------------------------------------

class Option(Model):
    value: Any
    label: str


class ElementDescriptor(Model):
    name: str
    label: str
    kind: str
    value: Any
    disabled: bool
    min: float | None = None
    max: float | None = None
    integer: bool = None
    optional: bool = None
    options: list[Option] = None
    shape: list[int] = None
    dtype: str = None
    defaultType: str = None
    selectionElements: list[str] = None
    itemPorts: list[str | None] = None


class PortDescriptor(Model):
    name: str
    direction: Literal["in", "out"]
    shape: list[int]
    accepts: list[int] = None
    adaptiveShape: bool = None
    variadic: bool = None


class NodeDescriptor(Model):
    id: str
    type: str
    elements: list[ElementDescriptor]
    ports: list[PortDescriptor]


class Snapshot(Model):
    graph: Graph
    nodes: list[NodeDescriptor]


class GraphState(Snapshot):
    """A snapshot with the revision it describes, for clients resynchronising over HTTP."""
    revision: int


# --- Catalog: how the editor presents each node type ----------------------------------------------------

ControlKind = Literal["port", "slider", "switch", "select", "axis", "text", "color", "interval", "array", "shape",
                      "curve", "reference", "node-reference", "sequence", "expression", "managed"]
Scale = Literal["linear", "logarithmic"]


class Bounds(Model):
    """Limits of a field that follow another field's value (e.g. a frequency range bounded by the sample rate)."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    source: str = Field(alias="from")
    min: float
    max: float


class FieldUi(Model):
    name: str
    control: ControlKind
    label: str = None
    unit: str = None
    scale: Scale = None
    min: float = None
    max: float = None
    item: Literal["reference", "node", "token"] = None
    nodeTypes: list[str] = None
    rebuild: bool = None
    bounds: Bounds = None
    matchInput: str = None
    ordered: bool = None
    hidden: bool = None
    portsPrefix: str = None
    channels: list[str] = None
    addPort: str = None


class ViewUi(Model):
    kind: Literal["bars", "history", "color", "lights", "trigger", "meter", "playlist"]
    data: str = None
    colors: str = None
    label: str = None
    series: list[str] = None
    open: bool = None
    unit: str = None
    xScale: Scale = None
    xMinField: str = None
    xMaxField: str = None


class NodeUi(Model):
    """A node class's `ui` attribute: its title, help text, one control per constructor parameter and its views."""
    title: str
    description: str
    category: str
    fields: list[FieldUi]
    views: list[ViewUi]
    actions: list[Literal["start", "stop"]] = None


class CatalogNode(NodeUi):
    type: str


# --- Player and generation ---------------------------------------------------------------------------

class Track(Model):
    id: str
    title: str
    artist: str
    duration: float
    loaded: bool
    downloadState: Literal["queued", "downloading", "ready", "failed"]


class PlayerState(Model):
    nodeId: str
    tracks: list[Track]
    loading: bool
    activeTrackId: str | None
    playing: bool
    position: float
    duration: float


class SearchTrack(Model):
    id: str
    title: str
    artist: str
    duration: float


class PlayerResults(Model):
    nodeId: str
    query: str
    tracks: list[SearchTrack]


class GenerationState(Model):
    status: Literal["idle", "running", "complete", "cancelled", "error"]
    message: str
    nodes: int
    mode: Literal["generate", "edit"]


class PreviewNode(Model):
    id: str
    type: str
    ports: list[PortDescriptor]


class GenerationPreview(Model):
    graph: Graph
    nodes: list[PreviewNode]


# --- Server events -------------------------------------------------------------------------------------

class StateUpdate(Model):
    """An element value, a node's new descriptor, or a batch of node positions."""
    nodeId: str = None
    element: str = None
    value: Any = None
    node: NodeDescriptor = None
    positions: dict[str, Position] = None


class GraphPatch(Model):
    """Changes since revision `base`: rebuild each list from its id order, preferring the items sent here."""
    base: int
    nodeOrder: list[str]
    connectionOrder: list[str]
    nodes: list[GraphNode]
    connections: list[Connection]
    descriptors: list[NodeDescriptor]


class HistoryUpdate(Model):
    canUndo: bool


class StreamValue(Model):
    nodeId: str
    element: str
    value: Any


class Frame(Model):
    sequence: int
    values: list[StreamValue]
    players: list[PlayerState]


class Ack(Model):
    command: str
    result: Any


class Error(Model):
    message: str
    nodeId: str = None
    processing: bool = None


EVENTS = {
    "graph.snapshot": Snapshot, "graph.patch": GraphPatch, "state.update": StateUpdate, "history.update": HistoryUpdate, "frame": Frame,
    "player.update": PlayerState, "jev.update": GenerationState,
    "jev.preview": GenerationPreview, "ack": Ack, "error": Error,
}


# --- Commands ------------------------------------------------------------------------------------------

class Command(Model):
    # Consecutive edits of one gesture share a group and undo together; arrange moves skip history.
    historyGroup: int | None = None
    recordHistory: bool = True


class Empty(Command):
    pass


class NodeIds(Command):
    nodeIds: list[str] = Field(min_length=1)


class GraphPaste(Command):
    graph: Graph
    position: Position


class GraphLoad(Command):
    graph: Graph | LegacyTemplate


class GraphRestore(Command):
    graph: Graph


class GraphMove(Command):
    positions: dict[str, Position]


class NodeType(Command):
    nodeType: str


class NodeAdd(Command):
    nodeType: str
    nodeId: str | None = None
    position: Position = [0, 0]
    parameters: dict[str, Any] = {}
    connections: list[Connection] = []


class NodeRef(Command):
    nodeId: str


class NodeMove(Command):
    nodeId: str
    position: Position


class NodeConfigure(Command):
    nodeId: str
    parameters: dict[str, Any]


class ConnectionAdd(Command):
    source: Endpoint
    target: Endpoint
    connectionId: str | None = None


class ConnectionRemove(Command):
    connectionId: str


class ElementSet(Command):
    nodeId: str
    element: str
    value: Any


class StreamsUpdate(Command):
    """Changes to the session's streamed ports; adding a stream twice or removing an absent one is harmless."""
    add: list[Endpoint] = []
    remove: list[Endpoint] = []


class FrameAck(Command):
    sequence: int


class PlayerPlay(Command):
    nodeId: str
    trackId: str | None = None


class PlayerSeek(Command):
    nodeId: str
    position: Finite


class PlayerSearch(Command):
    nodeId: str
    query: str


class PlaylistTrack(Command):
    nodeId: str
    trackId: str


class JevGenerate(Command):
    prompt: str = Field(min_length=1, max_length=16000)
    mode: Literal["generate", "edit"] = "generate"


COMMANDS = {
    "graph.get": Empty, "graph.copy": NodeIds, "graph.paste": GraphPaste, "graph.load": GraphLoad,
    "graph.move": GraphMove, "graph.restore": GraphRestore, "graph.undo": Empty,
    "node.describe": NodeType, "node.add": NodeAdd, "node.remove": NodeRef, "node.move": NodeMove,
    "node.configure": NodeConfigure, "node.start": NodeRef, "node.stop": NodeRef,
    "connection.add": ConnectionAdd, "connection.remove": ConnectionRemove, "element.set": ElementSet,
    "streams.update": StreamsUpdate, "frame.ack": FrameAck,
    "player.play": PlayerPlay, "player.pause": NodeRef, "player.seek": PlayerSeek, "player.search": PlayerSearch,
    "playlist.add": PlaylistTrack, "playlist.remove": PlaylistTrack,
    "jev.generate": JevGenerate, "jev.cancel": Empty,
}


def parse_command(kind, payload):
    """Validate a command where it enters; handlers receive every field, defaults filled in."""
    if kind not in COMMANDS:
        raise ValueError(f"Unknown route: {kind}")
    return COMMANDS[kind].model_validate(payload).model_dump()

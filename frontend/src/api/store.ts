import { createHttpClient, unwrap } from "./client.ts";
import { BackendConnection, type ConnectionStatus } from "./connection.ts";
import type {
  Message,
  Snapshot,
  NodeDescriptor,
  Endpoint,
  ArrayValue,
  PlayerState,
  Graph,
  GenerationPreview,
  GenerationState,
  GraphNode,
  Connection,
  GraphPatch,
} from "./protocol.ts";
import { encodeTemplate, decodeTemplate, emptyViewSettings, type DisplayState, type ViewSettings } from "./template.ts";

type Listener = () => void;
const keyOf = (nodeId: string, element: string) => JSON.stringify([nodeId, element]);
const nodeOf = (key: string) => (JSON.parse(key) as [string, string])[0];
/** Rebuild a list from its id order, preferring the items a patch sent. */
const merge = <T extends { id: string }>(items: T[], upserts: T[], order: string[]) => {
  const known = new Map([...items, ...upserts].map((item) => [item.id, item]));
  return order.map((id) => known.get(id)!);
};
// One id per browser tab scopes undo history; getRandomValues also works outside secure (https) contexts.
const tabId = () => Array.from(crypto.getRandomValues(new Uint8Array(8)), (byte) => byte.toString(16)).join("");
export const initialStatus = { connection: "offline" as ConnectionStatus, error: "", revision: 0, canUndo: false };
export const initialGeneration: GenerationState = { status: "idle", message: "", nodes: 0, mode: "generate" };

export class BackendStore {
  snapshot: Snapshot | null = null;
  /** Counts full snapshots: each one is a new graph (connection, loaded template, generated graph), edits are patches. */
  graphEpoch = 0;
  status = initialStatus;
  generation = initialGeneration;
  generationPreview: GenerationPreview | null = null;
  private display: DisplayState = {};
  private nodes = new Map<string, NodeDescriptor>();
  private originals = new Map<string, NodeDescriptor>();
  private arrays = new Map<string, ArrayValue>();
  private players = new Map<string, PlayerState>();
  private edits = new Map<string, { version: number; value: unknown }>();
  private version = 0;
  private historyGroup = 0;
  beginAction() {
    this.historyGroup++;
  }
  private listeners = new Map<string, Set<Listener>>();
  private streams = new Map<string, Endpoint>();
  /** The streams this tab's WebSocket session subscribed; a new session starts with none. */
  private subscribed = new Set<string>();
  private subscriptionsScheduled = false;
  private subscription: object | null = null;
  private streamReady = false;
  readonly connection: BackendConnection;
  readonly http: ReturnType<typeof createHttpClient>;

  constructor(
    baseUrl = "http://127.0.0.1:8000",
    fetch: typeof globalThis.fetch = (request) => globalThis.fetch(request),
  ) {
    this.http = createHttpClient(baseUrl, tabId(), fetch);
    this.connection = new BackendConnection(
      `${baseUrl.replace(/^http/, "ws")}/ws`,
      (message) => this.receive(message),
      (connection, detail) => {
        this.status = { ...this.status, connection, ...(detail ? { error: detail } : {}) };
        if (connection !== "connected") {
          this.subscription = null;
          this.streamReady = false;
          this.subscribed.clear();
        }
        if (connection === "offline") {
          this.subscribed.clear();
          this.edits.clear();
          this.generationPreview = null;
          this.emit("jev-preview");
          for (const node of this.originals.values()) this.updateNode(node);
        }
        this.emit("status");
      },
    );
  }

  private headers() {
    return { "X-History-Group": String(this.historyGroup) };
  }
  /**
   * Run an HTTP request and resolve once this tab's WebSocket state includes its effect (X-Revision), so callers
   * read their own writes. A lost connection releases the wait: the next snapshot brings the state anyway.
   */
  private call<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>) {
    return unwrap(request, (response) => this.reached(Number(response.headers.get("X-Revision"))));
  }
  private reached(revision: number) {
    return new Promise<void>((resolve) => {
      const check = () => {
        if (revision > this.status.revision && this.status.connection === "connected") return;
        off();
        resolve();
      };
      const off = this.subscribe("status", check);
      check();
    });
  }
  /** Run an HTTP command; a refusal is shown in the status bar and resolves to undefined. */
  private async attempt<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>) {
    try {
      return await this.call(request);
    } catch (error) {
      this.fail(error);
      return undefined;
    }
  }
  private fail(error: unknown) {
    this.status = { ...this.status, error: error instanceof Error ? error.message : String(error) };
    this.emit("status");
  }

  /** Playlist players over HTTP; their state streams back in frames and player.update events. */
  readonly playback = {
    play: (nodeId: string, trackId?: string) =>
      this.attempt(
        this.http.POST("/api/v1/players/{nodeId}/play", { params: { path: { nodeId } }, body: { trackId } }),
      ),
    pause: (nodeId: string) =>
      this.attempt(this.http.POST("/api/v1/players/{nodeId}/pause", { params: { path: { nodeId } } })),
    seek: (nodeId: string, position: number) =>
      this.attempt(
        this.http.POST("/api/v1/players/{nodeId}/seek", { params: { path: { nodeId } }, body: { position } }),
      ),
    search: (nodeId: string, query: string) =>
      this.attempt(
        this.http.GET("/api/v1/players/{nodeId}/search", { params: { path: { nodeId }, query: { query } } }),
      ),
    queue: (nodeId: string, trackId: string) =>
      this.attempt(
        this.http.POST("/api/v1/players/{nodeId}/playlist", { params: { path: { nodeId } }, body: { trackId } }),
      ),
    unqueue: (nodeId: string, trackId: string) =>
      this.attempt(
        this.http.DELETE("/api/v1/players/{nodeId}/playlist", { params: { path: { nodeId }, query: { trackId } } }),
      ),
  };

  /** Jev generations: accepted over HTTP (202), then reported by jev.update and jev.preview events. */
  readonly jev = {
    generate: (prompt: string, mode: "generate" | "edit") =>
      this.attempt(this.http.POST("/api/v1/generations", { body: { prompt, mode } })),
    cancel: () => this.attempt(this.http.DELETE("/api/v1/generations/current")),
  };

  /** Graph edits over HTTP; their effects reach every tab, this one included, as WebSocket patches. */
  readonly graph = {
    undo: () => this.attempt(this.http.POST("/api/v1/graph/undo", { headers: this.headers() })),
    copy: (nodeIds: string[]) =>
      this.attempt(this.http.POST("/api/v1/graph/copy", { body: { nodeIds }, headers: this.headers() })),
    paste: (graph: Graph, position: [number, number]) =>
      this.attempt(this.http.POST("/api/v1/graph/paste", { body: { graph, position }, headers: this.headers() })),
    move: (positions: Record<string, [number, number]>, recordHistory = true) =>
      this.attempt(
        this.http.PATCH("/api/v1/graph/positions", { body: { positions, recordHistory }, headers: this.headers() }),
      ),
    addNode: (body: {
      nodeType: string;
      nodeId: string;
      position: [number, number];
      parameters: Record<string, unknown>;
      connections: Connection[];
    }) => this.attempt(this.http.POST("/api/v1/nodes", { body, headers: this.headers() })),
    removeNode: (nodeId: string) =>
      this.attempt(
        this.http.DELETE("/api/v1/nodes/{nodeId}", { params: { path: { nodeId } }, headers: this.headers() }),
      ),
    configureNode: (nodeId: string, parameters: Record<string, unknown>) =>
      this.attempt(
        this.http.PUT("/api/v1/nodes/{nodeId}/parameters", {
          params: { path: { nodeId } },
          body: { parameters },
          headers: this.headers(),
        }),
      ),
    runNode: (nodeId: string, action: "start" | "stop" | "recalibrate") =>
      this.attempt(this.http.POST(`/api/v1/nodes/{nodeId}/${action}`, { params: { path: { nodeId } } })),
    connect: (source: Endpoint, target: Endpoint, connectionId?: string) =>
      this.attempt(
        this.http.POST("/api/v1/connections", { body: { source, target, connectionId }, headers: this.headers() }),
      ),
    disconnect: (connectionId: string) =>
      this.attempt(
        this.http.DELETE("/api/v1/connections/{connectionId}", {
          params: { path: { connectionId } },
          headers: this.headers(),
        }),
      ),
    describeType: (nodeType: string) =>
      this.call(this.http.GET("/api/v1/node-types/{nodeType}", { params: { path: { nodeType } } })),
  };

  subscribe(key: string, listener: Listener) {
    const set = this.listeners.get(key) ?? new Set();
    set.add(listener);
    this.listeners.set(key, set);
    return () => {
      set.delete(listener);
      if (!set.size && this.listeners.get(key) === set) this.listeners.delete(key);
    };
  }
  private emit(key: string) {
    this.listeners.get(key)?.forEach((listener) => listener());
  }
  node(id: string) {
    return this.nodes.get(id) ?? null;
  }
  array(nodeId: string, element: string) {
    return this.arrays.get(keyOf(nodeId, element)) ?? null;
  }
  player(id: string) {
    return this.players.get(id) ?? null;
  }

  viewSettings(nodeId: string, viewId: string) {
    return this.display[nodeId]?.[viewId] ?? emptyViewSettings;
  }
  setViewSettings(nodeId: string, viewId: string, changes: Partial<ViewSettings>) {
    this.display = {
      ...this.display,
      [nodeId]: { ...this.display[nodeId], [viewId]: { ...this.viewSettings(nodeId, viewId), ...changes } },
    };
    this.emit(`display:${keyOf(nodeId, viewId)}`);
  }
  private replaceDisplay(display: DisplayState) {
    const keys = new Set(
      [...Object.entries(this.display), ...Object.entries(display)].flatMap(([nodeId, views]) =>
        Object.keys(views).map((viewId) => keyOf(nodeId, viewId)),
      ),
    );
    this.display = display;
    for (const key of keys) this.emit(`display:${key}`);
  }
  async exportTemplate() {
    const { graph } = await this.call(this.http.GET("/api/v1/graph"));
    // openapi-fetch widens the schema's [x, y] position tuples to number[]; the backend validated them.
    return encodeTemplate({ version: 1, graph: graph as Graph, ui: this.display });
  }
  /** View settings of a template being loaded; installed with its snapshot so the first layout sees them. */
  private incomingDisplay: DisplayState | null = null;
  async importTemplate(bytes: ArrayBuffer | Uint8Array) {
    const template = decodeTemplate(bytes);
    this.incomingDisplay = template.ui;
    try {
      await this.call(this.http.PUT("/api/v1/graph", { body: { graph: template.graph }, headers: this.headers() }));
      if (this.incomingDisplay) this.replaceDisplay(this.incomingDisplay);
    } finally {
      this.incomingDisplay = null;
    }
  }

  watchArray(nodeId: string, element: string, listener: Listener) {
    const key = keyOf(nodeId, element);
    const off = this.subscribe(`array:${key}`, listener);
    this.streams.set(key, { nodeId, element });
    this.syncSubscriptions();
    return () => {
      off();
      if (!this.listeners.get(`array:${key}`)?.size) this.streams.delete(key);
      this.syncSubscriptions();
    };
  }
  /** Coalesce view remounts and send only stream differences, one acknowledged update at a time. */
  private syncSubscriptions() {
    if (this.subscriptionsScheduled || this.subscription) return;
    this.subscriptionsScheduled = true;
    queueMicrotask(() => {
      this.subscriptionsScheduled = false;
      if (this.status.connection !== "connected" || !this.streamReady || !this.snapshot) return;
      const wanted = new Set(
        [...this.streams]
          .flatMap(([key, item]) =>
            this.nodes.get(item.nodeId)?.ports.some((port) => port.name === item.element) ? [key] : [],
          )
          .sort(),
      );
      const add = [...wanted].filter((key) => !this.subscribed.has(key));
      const remove = [...this.subscribed].filter((key) => !wanted.has(key)).sort();
      if (!add.length && !remove.length) return;
      const endpoints = (keys: string[]) =>
        keys.map((key) => {
          const [nodeId, element] = JSON.parse(key) as [string, string];
          return { nodeId, element };
        });
      const subscription = {};
      this.subscription = subscription;
      void this.connection.request("streams.update", { add: endpoints(add), remove: endpoints(remove) }).then(
        () => {
          if (this.subscription !== subscription) return;
          this.subscribed = wanted;
          this.subscription = null;
          this.syncSubscriptions();
        },
        (error: unknown) => {
          if (this.subscription !== subscription) return;
          this.subscription = null;
          this.subscribed.clear();
          this.fail(error);
        },
      );
    });
  }

  private updateNode(node: NodeDescriptor) {
    this.originals.set(node.id, node);
    this.nodes.set(node.id, {
      ...node,
      elements: node.elements.map((element) => {
        const edit = this.edits.get(keyOf(node.id, element.name));
        return edit ? { ...element, value: edit.value } : element;
      }),
    });
    this.emit(`node:${node.id}`);
  }

  // Snapshots, frames and generation events carry their own state; every other message may advance the revision.
  private readonly exclusive: Record<string, (message: Message) => void> = {
    "jev.preview": (message) => this.receivePreview(message),
    "jev.update": (message) => this.receiveGeneration(message),
    error: (message) => this.receiveError(message),
    "graph.snapshot": (message) => this.receiveSnapshot(message),
    "graph.patch": (message) => this.receivePatch(message),
    frame: (message) => this.receiveFrame(message),
  };
  private readonly updates: Record<string, (message: Message) => void> = {
    "state.update": (message) => this.receiveState(message),
    "history.update": (message) => this.receiveHistory(message),
    "player.update": (message) => this.receivePlayer(message),
  };

  private receive(message: Message) {
    const exclusive = this.exclusive[message.type];
    if (exclusive) return exclusive(message);
    // Apply first: a revision is announced only once the state it names is in place.
    this.updates[message.type]?.(message);
    this.advanceRevision(message.revision);
  }
  private receivePreview(message: Message) {
    this.generationPreview = message.payload as GenerationPreview;
    this.emit("jev-preview");
  }
  private receiveGeneration(message: Message) {
    const generation = message.payload as GenerationState;
    if (generation.status === "complete" && this.generation.status === "running" && generation.mode === "generate") {
      this.replaceDisplay({});
    }
    this.generation = generation;
    if (generation.status !== "running") {
      this.generationPreview = null;
      this.emit("jev-preview");
    }
    this.emit("jev");
  }
  private receiveError(message: Message) {
    this.status = { ...this.status, error: String(message.payload.message) };
    this.emit("status");
  }
  private pruneDisplay(ids: Set<string>) {
    if (Object.keys(this.display).some((id) => !ids.has(id)))
      this.replaceDisplay(Object.fromEntries(Object.entries(this.display).filter(([id]) => ids.has(id))));
  }
  private receiveSnapshot(message: Message) {
    this.streamReady = true;
    this.snapshot = message.payload as unknown as Snapshot;
    if (this.incomingDisplay) this.replaceDisplay(this.incomingDisplay);
    this.incomingDisplay = null;
    this.pruneDisplay(new Set(this.snapshot.graph.nodes.map((node) => node.id)));
    this.arrays.clear();
    this.players.clear();
    this.nodes.clear();
    this.originals.clear();
    this.edits.clear();
    for (const node of this.snapshot.nodes) this.updateNode(node);
    this.status = { ...this.status, error: "", revision: message.revision };
    this.graphEpoch++;
    // The new epoch and its graph reach React together, so no view of the previous graph acts on the new one.
    this.emit("epoch");
    this.emit("status");
    this.emit("graph");
    this.syncSubscriptions();
  }
  /** Apply an edit's delta; untouched nodes keep their descriptor, optimistic edits and streamed arrays. */
  private receivePatch(message: Message) {
    const patch = message.payload as unknown as GraphPatch;
    if (!this.snapshot || patch.base !== this.status.revision) return void this.resync();
    const kept = new Set(patch.nodeOrder);
    for (const id of [...this.originals.keys()]) if (!kept.has(id)) this.forgetNode(id);
    this.pruneDisplay(kept);
    this.snapshot = {
      graph: {
        nodes: merge<GraphNode>(this.snapshot.graph.nodes, patch.nodes, patch.nodeOrder),
        connections: merge<Connection>(this.snapshot.graph.connections, patch.connections, patch.connectionOrder),
      },
      nodes: merge<NodeDescriptor>(this.snapshot.nodes, patch.descriptors, patch.nodeOrder),
    };
    for (const node of patch.descriptors) this.updateNode(node);
    this.status = { ...this.status, error: "", revision: message.revision };
    this.emit("status");
    this.emit("graph");
    this.syncSubscriptions();
  }
  private forgetNode(id: string) {
    for (const map of [this.arrays, this.edits])
      for (const key of [...map.keys()]) if (nodeOf(key) === id) map.delete(key);
    this.originals.delete(id);
    this.nodes.delete(id);
    this.players.delete(id);
    this.emit(`node:${id}`);
  }
  /** Replace local state with the backend's when a patch does not follow the revision this tab holds. */
  async resync() {
    const state = await this.attempt(this.http.GET("/api/v1/graph"));
    if (state) this.receiveSnapshot({ type: "graph.snapshot", revision: state.revision, payload: state });
  }
  private receiveFrame(message: Message) {
    try {
      if (message.revision !== this.status.revision) return;
      const changed = new Set<string>();
      for (const item of message.payload.values as { nodeId: string; element: string; value: ArrayValue }[]) {
        const key = keyOf(item.nodeId, item.element);
        this.arrays.set(key, item.value);
        changed.add(`array:${key}`);
      }
      for (const player of message.payload.players as PlayerState[]) {
        this.players.set(player.nodeId, player);
        changed.add(`player:${player.nodeId}`);
      }
      for (const key of changed) this.emit(key);
    } finally {
      this.connection.send("frame.ack", { sequence: message.payload.sequence });
    }
  }
  private advanceRevision(revision: number) {
    if (revision <= this.status.revision) return;
    this.status = { ...this.status, revision };
    this.emit("status");
  }
  private receiveState(message: Message) {
    if (message.payload.node) this.updateNode(message.payload.node as NodeDescriptor);
    if (message.payload.positions && this.snapshot) {
      const positions = message.payload.positions as Record<string, [number, number]>;
      this.snapshot = {
        ...this.snapshot,
        graph: {
          ...this.snapshot.graph,
          nodes: this.snapshot.graph.nodes.map((node) =>
            positions[node.id] ? { ...node, position: positions[node.id] } : node,
          ),
        },
      };
      this.emit("graph");
    }
  }
  private receiveHistory(message: Message) {
    this.status = { ...this.status, canUndo: Boolean(message.payload.canUndo) };
    this.emit("status");
  }
  private receivePlayer(message: Message) {
    this.setPlayer(message.payload as PlayerState);
  }
  private setPlayer(player: PlayerState) {
    this.players.set(player.nodeId, player);
    this.emit(`player:${player.nodeId}`);
  }

  async command(type: string, payload: Record<string, unknown> = {}) {
    try {
      return await this.connection.request(type, { ...payload, historyGroup: this.historyGroup });
    } catch (error) {
      this.status = { ...this.status, error: error instanceof Error ? error.message : String(error) };
      this.emit("status");
      return undefined;
    }
  }

  async setElement(nodeId: string, element: string, value: unknown) {
    const key = keyOf(nodeId, element);
    const version = ++this.version;
    this.edits.set(key, { version, value });
    const node = this.originals.get(nodeId);
    if (node) this.updateNode(node);
    await this.command("element.set", { nodeId, element, value });
    if (this.edits.get(key)?.version === version) {
      this.edits.delete(key);
      const current = this.originals.get(nodeId);
      if (current) this.updateNode(current);
    }
  }
}

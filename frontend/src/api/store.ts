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
} from "./protocol.ts";
import { encodeTemplate, decodeTemplate, emptyViewSettings, type DisplayState, type ViewSettings } from "./template.ts";

type Listener = () => void;
const keyOf = (nodeId: string, element: string) => JSON.stringify([nodeId, element]);
export const initialStatus = { connection: "offline" as ConnectionStatus, error: "", revision: 0, canUndo: false };
export type GenerationState = {
  status: "idle" | "running" | "complete" | "cancelled" | "error";
  message: string;
  nodes: number;
  mode: "generate" | "edit";
};
export const initialGeneration: GenerationState = { status: "idle", message: "", nodes: 0, mode: "generate" };

export class BackendStore {
  snapshot: Snapshot | null = null;
  templateRevision = 0;
  status = initialStatus;
  generation = initialGeneration;
  generationPreview: GenerationPreview | null = null;
  private display: DisplayState = {};
  private nodes = new Map<string, NodeDescriptor>();
  private originals = new Map<string, NodeDescriptor>();
  private arrays = new Map<string, ArrayValue>();
  private players = new Map<string, PlayerState>();
  private results = new Map<string, { query: string; tracks: PlayerState["tracks"] }>();
  private edits = new Map<string, { version: number; value: unknown }>();
  private version = 0;
  private historyGroup = 0;
  beginAction() {
    this.historyGroup++;
  }
  private listeners = new Map<string, Set<Listener>>();
  private streams = new Map<string, Endpoint>();
  readonly connection = new BackendConnection(
    (message) => this.receive(message),
    (connection) => {
      this.status = { ...this.status, connection };
      if (connection === "offline") {
        this.edits.clear();
        this.generationPreview = null;
        this.emit("jev-preview");
        for (const node of this.originals.values()) this.updateNode(node);
      }
      this.emit("status");
    },
  );

  subscribe(key: string, listener: Listener) {
    const set = this.listeners.get(key) ?? new Set();
    set.add(listener);
    this.listeners.set(key, set);
    return () => {
      set.delete(listener);
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
  searchResults(id: string) {
    return this.results.get(id) ?? null;
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
    const { graph } = (await this.connection.request("graph.get")) as { graph: Graph };
    return encodeTemplate({ version: 1, graph, ui: this.display });
  }
  async importTemplate(bytes: ArrayBuffer | Uint8Array) {
    const template = decodeTemplate(bytes);
    await this.connection.request("graph.load", { graph: template.graph });
    this.replaceDisplay(template.ui);
    this.templateRevision++;
    this.emit("template");
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
  private syncSubscriptions() {
    if (this.status.connection !== "connected" || !this.snapshot) return;
    const elements = [...this.streams.values()].filter((item) =>
      this.nodes.get(item.nodeId)?.ports.some((port) => port.name === item.element),
    );
    void this.command("subscribe", { elements });
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
    frame: (message) => this.receiveFrame(message),
  };
  private readonly updates: Record<string, (message: Message) => void> = {
    "state.update": (message) => this.receiveState(message),
    "history.update": (message) => this.receiveHistory(message),
    "player.update": (message) => this.receivePlayer(message),
    "player.results": (message) => this.receiveResults(message),
  };

  private receive(message: Message) {
    const exclusive = this.exclusive[message.type];
    if (exclusive) return exclusive(message);
    this.advanceRevision(message.revision);
    this.updates[message.type]?.(message);
  }
  private receivePreview(message: Message) {
    this.generationPreview = message.payload as GenerationPreview;
    this.emit("jev-preview");
  }
  private receiveGeneration(message: Message) {
    const generation = message.payload as GenerationState;
    if (generation.status === "complete" && this.generation.status === "running" && generation.mode === "generate") {
      this.replaceDisplay({});
      this.templateRevision++;
      this.emit("template");
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
  private receiveSnapshot(message: Message) {
    this.snapshot = message.payload as unknown as Snapshot;
    const ids = new Set(this.snapshot.graph.nodes.map((node) => node.id));
    if (Object.keys(this.display).some((id) => !ids.has(id)))
      this.replaceDisplay(Object.fromEntries(Object.entries(this.display).filter(([id]) => ids.has(id))));
    this.arrays.clear();
    this.players.clear();
    this.nodes.clear();
    this.originals.clear();
    this.edits.clear();
    for (const node of this.snapshot.nodes) this.updateNode(node);
    this.status = { ...this.status, error: "", revision: message.revision ?? 0 };
    this.emit("status");
    this.emit("graph");
    this.syncSubscriptions();
  }
  private receiveFrame(message: Message) {
    try {
      if (message.revision !== this.status.revision) return;
      for (const item of message.payload.values as { nodeId: string; element: string; value: ArrayValue }[]) {
        const key = keyOf(item.nodeId, item.element);
        this.arrays.set(key, item.value);
        this.emit(`array:${key}`);
      }
      for (const player of message.payload.players as PlayerState[]) this.setPlayer(player);
    } finally {
      this.connection.send("frame.ack", { sequence: message.payload.sequence });
    }
  }
  private advanceRevision(revision: number | undefined) {
    if (revision === undefined || revision <= this.status.revision) return;
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
  private receiveResults(message: Message) {
    this.results.set(
      String(message.payload.nodeId),
      message.payload as { query: string; tracks: PlayerState["tracks"] },
    );
    this.emit(`results:${message.payload.nodeId}`);
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

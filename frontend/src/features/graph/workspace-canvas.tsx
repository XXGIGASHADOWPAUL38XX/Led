import {
  Background,
  BackgroundVariant,
  ReactFlow,
  applyEdgeChanges,
  applyNodeChanges,
  useConnection,
  useNodesInitialized,
  useReactFlow,
  useStore,
  useUpdateNodeInternals,
  useViewport,
  type Connection as FlowConnection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeProps,
  type ReactFlowProps,
} from "@xyflow/react";
import {
  type MouseEvent as ReactMouseEvent,
  type Ref,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import type { Endpoint, Graph } from "@/api/protocol";
import { useBackend } from "@/api/backend-context";
import { useBackendStatus } from "@/api/hooks";
import { compatiblePorts } from "@/features/nodes/configuration";
import { LiveNode } from "../nodes/live-node";
import { layoutGraph } from "./graph-layout";
import { isTyping } from "./shortcuts";
import { compatibleTerminals, terminalKey } from "./terminal-compatibility";
import { useNodeClipboard } from "./use-node-clipboard";
import { WorkspaceContext } from "./workspace-context";

export type CanvasHandle = { insertionPosition: () => [number, number] };

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 2;
const nodeTypes = { live: ({ id, selected }: NodeProps) => <LiveNode id={id} selected={selected} /> };

/** Mirror the backend graph; keep React Flow's own state (selection, measures, active drag) per id. */
function toNodes(graph: Graph, previous: Node[]): Node[] {
  const known = new Map(previous.map((node) => [node.id, node]));
  return graph.nodes.map(({ id, position: [x, y] }) => {
    const node = known.get(id);
    if (node?.dragging) return node;
    return node
      ? { ...node, position: { x, y } }
      : { id, type: "live", position: { x, y }, dragHandle: ".node-drag-handle", data: {} };
  });
}
function toEdges(graph: Graph, previous: Edge[]): Edge[] {
  const selected = new Set(previous.filter((edge) => edge.selected).map((edge) => edge.id));
  return graph.connections.map(({ id, source, target }) => ({
    id,
    source: source.nodeId,
    sourceHandle: source.element,
    target: target.nodeId,
    targetHandle: target.element,
    reconnectable: "target",
    selected: selected.has(id),
    ariaLabel: `${source.nodeId}.${source.element} → ${target.nodeId}.${target.element}`,
  }));
}
const endpoint = (nodeId: string, element: string | null | undefined): Endpoint => ({ nodeId, element: element! });
const attached = (edge: Edge, key: string) =>
  terminalKey(endpoint(edge.source, edge.sourceHandle), "output") === key ||
  terminalKey(endpoint(edge.target, edge.targetHandle), "input") === key;

export function WorkspaceCanvas({ graph, ref }: { graph: Graph; ref?: Ref<CanvasHandle> }) {
  const backend = useBackend();
  const status = useBackendStatus();
  const flow = useReactFlow();
  const { zoom } = useViewport();
  const initialized = useNodesInitialized();
  const [source, setSource] = useState(graph);
  const [nodes, setNodes] = useState(() => toNodes(graph, []));
  const [edges, setEdges] = useState(() => toEdges(graph, []));
  if (source !== graph) {
    setSource(graph);
    setNodes((previous) => toNodes(graph, previous));
    setEdges((previous) => toEdges(graph, previous));
  }

  // React Flow drops a node's handle bounds when it re-adopts our nodes between measuring them and our applying that
  // measure (e.g. a paste selection landing meanwhile); the node keeps its size but never draws its wires again.
  const unbounded = useStore((state) =>
    [...state.nodeLookup.values()]
      .filter((node) => node.measured.width && !node.internals.handleBounds)
      .map((node) => node.id)
      .join("\n"),
  );
  const updateNodeInternals = useUpdateNodeInternals();
  useEffect(() => {
    if (unbounded) updateNodeInternals(unbounded.split("\n"));
  }, [unbounded, updateNodeInternals]);

  const pointer = useRef<{ x: number; y: number } | null>(null);
  const wrapper = useRef<HTMLDivElement>(null);
  const insertionPosition = useCallback((): [number, number] => {
    const rect = wrapper.current!.getBoundingClientRect();
    const { x, y } = flow.screenToFlowPosition(
      pointer.current ?? { x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 },
    );
    return [x, y];
  }, [flow]);
  useImperativeHandle(ref, () => ({ insertionPosition }), [insertionPosition]);
  const selectNodes = useCallback(
    (ids: string[]) => setNodes((items) => items.map((node) => ({ ...node, selected: ids.includes(node.id) }))),
    [],
  );
  const selectedNodes = useCallback(() => nodes.filter((node) => node.selected).map((node) => node.id), [nodes]);
  useNodeClipboard(insertionPosition, selectedNodes, selectNodes);

  // A port has no selection of its own: clicking it selects its wires, which Delete then removes.
  const selectPort = useCallback((key: string, extend: boolean) => {
    if (!extend) setNodes((items) => items.map((node) => (node.selected ? { ...node, selected: false } : node)));
    setEdges((items) =>
      items.map((edge) => ({ ...edge, selected: attached(edge, key) || (extend && Boolean(edge.selected)) })),
    );
  }, []);
  const disconnect = useCallback(
    (key: string) => {
      for (const edge of edges)
        if (attached(edge, key)) void backend.command("connection.remove", { connectionId: edge.id });
    },
    [backend, edges],
  );
  const origin = useConnection((connection) =>
    connection.inProgress
      ? terminalKey(
          endpoint(connection.fromHandle.nodeId, connection.fromHandle.id),
          connection.fromHandle.type === "source" ? "output" : "input",
        )
      : null,
  );
  const compatible = useMemo(() => {
    if (!origin) return null;
    const [nodeId, element, direction] = JSON.parse(origin) as [string, string, "input" | "output"];
    const descriptors = graph.nodes.flatMap((node) => backend.node(node.id) ?? []);
    return compatibleTerminals(descriptors, { nodeId, element }, direction);
  }, [backend, origin, graph]);
  const linked = useMemo(
    () =>
      new Set(
        graph.connections.flatMap((edge) => [terminalKey(edge.source, "output"), terminalKey(edge.target, "input")]),
      ),
    [graph],
  );
  const context = useMemo(
    () => ({ compatible, origin, linked, selectPort, disconnect }),
    [compatible, origin, linked, selectPort, disconnect],
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((items) => applyNodeChanges(changes, items));
      // Drag ends and arrow-key moves both report a settled position; one graph.move commits them.
      const moved = changes.flatMap((change) =>
        change.type === "position" && change.dragging === false && change.position
          ? [[change.id, [change.position.x, change.position.y]] as const]
          : [],
      );
      if (moved.length)
        void backend.command("graph.move", { positions: Object.fromEntries(moved) }).then((result) => {
          if (result === undefined) setNodes((items) => toNodes(graph, items));
        });
    },
    [backend, graph],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) =>
      setEdges((items) =>
        applyEdgeChanges(
          changes.filter((change) => change.type !== "remove"),
          items,
        ),
      ),
    [],
  );
  const isValidConnection = useCallback(
    (connection: FlowConnection | Edge) => {
      const output = backend
        .node(connection.source)
        ?.ports.find((port) => port.name === connection.sourceHandle && port.direction === "out");
      const input = backend
        .node(connection.target)
        ?.ports.find((port) => port.name === connection.targetHandle && port.direction === "in");
      return Boolean(output && input && connection.source !== connection.target && compatiblePorts(output, input));
    },
    [backend],
  );
  const onConnect = useCallback(
    (connection: FlowConnection) => {
      void backend.command("connection.add", {
        source: endpoint(connection.source, connection.sourceHandle),
        target: endpoint(connection.target, connection.targetHandle),
      });
    },
    [backend],
  );
  const onReconnect = useCallback(
    (edge: Edge, connection: FlowConnection) => {
      void backend.command("connection.add", {
        source: endpoint(connection.source, connection.sourceHandle),
        target: endpoint(connection.target, connection.targetHandle),
        connectionId: edge.id,
      });
    },
    [backend],
  );
  // A wire leaves an input by its reconnect anchor or by dragging the input terminal itself. Dropping it
  // away from any terminal disconnects; a press without movement is a terminal click.
  const pressed = useRef({ x: 0, y: 0 });
  const press = useCallback((event: MouseEvent | TouchEvent | ReactMouseEvent) => {
    const point = "changedTouches" in event ? event.changedTouches[0] : event;
    pressed.current = { x: point.clientX, y: point.clientY };
  }, []);
  const moved = (event: MouseEvent | TouchEvent) => {
    const point = "changedTouches" in event ? event.changedTouches[0] : event;
    return Math.hypot(point.clientX - pressed.current.x, point.clientY - pressed.current.y) >= 4;
  };
  const onReconnectEnd: NonNullable<ReactFlowProps["onReconnectEnd"]> = (event, edge, _, state) => {
    if (state.isValid) return;
    const key = terminalKey(endpoint(edge.target, edge.targetHandle), "input");
    if (!moved(event)) selectPort(key, event.ctrlKey || event.metaKey);
    else if (!state.toHandle) void backend.command("connection.remove", { connectionId: edge.id });
  };
  const onConnectEnd: NonNullable<ReactFlowProps["onConnectEnd"]> = (event, state) => {
    if (state.isValid || state.toHandle || state.fromHandle?.type !== "target" || !moved(event)) return;
    disconnect(terminalKey(endpoint(state.fromHandle.nodeId, state.fromHandle.id), "input"));
  };
  const onBeforeDelete: NonNullable<ReactFlowProps["onBeforeDelete"]> = useCallback(
    // Delete only acts on a wire selection; nodes have an explicit Remove button, and a node selection
    // (which also selects the wires between its nodes) is left untouched.
    async ({ nodes, edges }) => !nodes.length && !document.querySelector("dialog[open]") && { nodes: [], edges },
    [],
  );
  const onEdgesDelete = useCallback(
    (deleted: Edge[]) => {
      for (const edge of deleted) void backend.command("connection.remove", { connectionId: edge.id });
    },
    [backend],
  );

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (isTyping() || document.querySelector("dialog[open]")) return;
      if (event.key === "Escape") {
        setNodes((items) => items.map((node) => (node.selected ? { ...node, selected: false } : node)));
        setEdges((items) => items.map((edge) => (edge.selected ? { ...edge, selected: false } : edge)));
      }
      if (!(event.metaKey || event.ctrlKey) || !["+", "=", "-", "0"].includes(event.key)) return;
      event.preventDefault();
      if (event.key === "0") void flow.zoomTo(1);
      else if (event.key === "-") void flow.zoomOut();
      else void flow.zoomIn();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [flow]);

  const layout = useCallback(() => {
    const sizes = new Map(
      flow
        .getNodes()
        .map((node) => [node.id, { width: node.measured?.width ?? 0, height: node.measured?.height ?? 0 }]),
    );
    return layoutGraph(graph, sizes);
  }, [flow, graph]);
  const [arranging, setArranging] = useState(false);
  const arrange = async () => {
    setArranging(true);
    try {
      await backend.command("graph.move", { positions: layout() });
    } finally {
      setArranging(false);
    }
  };
  // Graphs without positions (e.g. from the generator) are laid out once their nodes are measured.
  const arranged = useRef("");
  useEffect(() => {
    const key = JSON.stringify([graph.nodes.map((node) => node.id), graph.connections]);
    if (
      !initialized ||
      status.connection !== "connected" ||
      graph.nodes.length < 2 ||
      !graph.nodes.every((node) => node.position.every((coordinate) => coordinate === 0)) ||
      arranged.current === key
    )
      return;
    arranged.current = key;
    void backend
      .command("graph.move", { positions: layout(), recordHistory: false })
      .then(() => requestAnimationFrame(() => void flow.fitView()));
  }, [backend, graph, initialized, status.connection, layout, flow]);

  return (
    <WorkspaceContext value={context}>
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={arranging || !graph.nodes.length || status.connection !== "connected"}
          onClick={() => {
            void arrange();
          }}
          className="rounded border border-white/10 px-3 py-2 text-xs text-zinc-300 hover:bg-white/5 disabled:opacity-40"
        >
          {arranging ? "Arranging…" : "Arrange nodes"}
        </button>
        <div
          role="group"
          aria-label="Workspace zoom"
          className="flex items-center rounded border border-white/10 text-xs text-zinc-300"
        >
          <button
            type="button"
            aria-label="Zoom out"
            disabled={zoom <= MIN_ZOOM}
            onClick={() => void flow.zoomOut()}
            className="px-3 py-2 disabled:opacity-30"
          >
            −
          </button>
          <button
            type="button"
            aria-label="Reset zoom"
            onClick={() => void flow.zoomTo(1)}
            className="w-14 py-2 font-mono text-[10px]"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            aria-label="Zoom in"
            disabled={zoom >= MAX_ZOOM}
            onClick={() => void flow.zoomIn()}
            className="px-3 py-2 disabled:opacity-30"
          >
            +
          </button>
        </div>
      </div>
      <p className="text-[10px] text-zinc-500">
        Drag empty space to select nodes · Ctrl/Cmd-click to extend selection · Drag a node header to move the selection
        · Drag terminals to connect · Click a terminal to select its wires
      </p>
      <div
        ref={wrapper}
        onPointerMove={(event) => {
          pointer.current = { x: event.clientX, y: event.clientY };
        }}
        className="h-[75vh] min-h-48 overflow-hidden rounded-xl border border-white/5"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onReconnect={onReconnect}
          onConnectStart={press}
          onConnectEnd={onConnectEnd}
          onReconnectStart={press}
          onReconnectEnd={onReconnectEnd}
          isValidConnection={isValidConnection}
          onBeforeDelete={onBeforeDelete}
          onEdgesDelete={onEdgesDelete}
          connectOnClick={false}
          deleteKeyCode={["Delete", "Backspace"]}
          multiSelectionKeyCode={["Control", "Meta"]}
          selectionOnDrag
          panOnDrag={[1, 2]}
          panOnScroll
          zoomActivationKeyCode={["Control", "Meta"]}
          minZoom={MIN_ZOOM}
          maxZoom={MAX_ZOOM}
          colorMode="dark"
          fitView
        >
          <Background variant={BackgroundVariant.Dots} color="#34353f" gap={24} size={2} />
        </ReactFlow>
      </div>
    </WorkspaceContext>
  );
}

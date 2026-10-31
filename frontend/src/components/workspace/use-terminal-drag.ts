"use client";

import { type RefObject, useCallback, useEffect, useRef, useState } from "react";
import { backend } from "@/lib/backend/store";
import type { Connection, Endpoint, Graph } from "@/lib/backend/protocol";
import { compatiblePorts } from "@/lib/nodes/configuration";
import { terminalKey } from "./terminal";
import { connectionPath, type Point } from "./connection-path";
import type { CanvasDrag } from "./use-canvas-viewport";
import { compatibleTerminals } from "./terminal-compatibility";

function port(key: string) {
  const [nodeId, element, direction] = JSON.parse(key) as [string, string, "input" | "output"];
  return { endpoint: { nodeId, element }, direction };
}

/** Keep dragging local; submit one validated graph edit when the pointer is released. */
export function useTerminalDrag(graph: Graph, container: RefObject<HTMLDivElement | null>, terminals: Map<string, HTMLElement>, zoom: number, { toCanvas: point, startNodeDrag, moveNodeDrag, cancelNodeDrag }: CanvasDrag) {
  const [preview, setPreview] = useState("");
  const [compatible, setCompatible] = useState<Set<string> | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const active = useRef<{ key: string; anchor: Point; forward: boolean; start: Point; edge?: Connection } | null>(null);
  const cancel = useCallback(() => {
    if (active.current) cancelNodeDrag();
    active.current = null; setPreview(""); setCompatible(null); setDragging(null);
  }, [cancelNodeDrag]);
  useEffect(() => { cancel(); }, [graph, zoom, cancel]);
  const update = useCallback((cursor: Point) => {
    const drag = active.current;
    if (drag) setPreview(drag.forward ? connectionPath(drag.anchor, cursor) : connectionPath(cursor, drag.anchor));
  }, []);
  const move = useCallback((x: number, y: number) => {
    if (active.current) moveNodeDrag(x, y);
  }, [moveNodeDrag]);
  const start = useCallback((key: string, x: number, y: number) => {
    if (backend.status.connection !== "connected") return;
    const terminal = port(key);
    const edge = terminal.direction === "input" ? graph.connections.find((edge) => terminalKey(edge.target, "input") === key) : undefined;
    const anchorKey = edge ? terminalKey(edge.source, "output") : key;
    const rect = terminals.get(anchorKey)!.getBoundingClientRect();
    const nodes = graph.nodes.flatMap((node) => backend.node(node.id) ?? []);
    setCompatible(compatibleTerminals(nodes, edge?.source ?? terminal.endpoint, edge ? "output" : terminal.direction));
    setDragging(key);
    active.current = { key, anchor: point(rect.left + rect.width / 2, rect.top + rect.height / 2), forward: Boolean(edge) || terminal.direction === "output", start: { x, y }, edge };
    startNodeDrag(x, y, update);
    update(point(x, y));
  }, [graph, terminals, point, startNodeDrag, update]);
  const finish = useCallback((x: number, y: number) => {
    const drag = active.current;
    cancel();
    if (!drag || Math.hypot(x - drag.start.x, y - drag.start.y) < 4) return;
    const element = document.elementFromPoint(x, y)?.closest<HTMLElement>("[data-terminal]");
    if (!element || !container.current!.contains(element)) {
      if (drag.edge) void backend.command("connection.remove", { connectionId: drag.edge.id });
      return;
    }
    const key = element.dataset.terminal!;
    if (key === drag.key) return;
    const from = port(drag.key), to = port(key);
    let source: Endpoint, target: Endpoint;
    if (from.direction === "output" && to.direction === "input") { source = from.endpoint; target = to.endpoint; }
    else if (from.direction === "input" && to.direction === "output") { source = to.endpoint; target = from.endpoint; }
    else if (from.direction === "input" && to.direction === "input" && drag.edge) { source = drag.edge.source; target = to.endpoint; }
    else return;
    const output = backend.node(source.nodeId)?.ports.find((port) => port.name === source.element && port.direction === "out");
    const input = backend.node(target.nodeId)?.ports.find((port) => port.name === target.element && port.direction === "in");
    if (source.nodeId === target.nodeId || !output || !input || !compatiblePorts(output, input)) return;
    void backend.command("connection.add", { source, target, ...(drag.edge ? { connectionId: drag.edge.id } : {}) });
  }, [cancel, container]);
  const disconnect = useCallback((key: string) => {
    for (const edge of graph.connections) if (terminalKey(edge.source, "output") === key || terminalKey(edge.target, "input") === key) {
      void backend.command("connection.remove", { connectionId: edge.id });
    }
  }, [graph]);
  return { preview, compatible, dragging, start, move, finish, cancel, disconnect };
}

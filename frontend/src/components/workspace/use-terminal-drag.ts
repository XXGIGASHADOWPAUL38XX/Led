"use client";

import { type RefObject, useCallback, useEffect, useRef, useState } from "react";
import { backend } from "@/lib/backend/store";
import type { Connection, Endpoint, Graph } from "@/lib/backend/protocol";
import { compatiblePorts } from "@/lib/nodes/configuration";
import { terminalKey } from "./terminal";
import { connectionPath, type Point } from "./connection-path";

function port(key: string) {
  const [nodeId, element, direction] = JSON.parse(key) as [string, string, "input" | "output"];
  return { endpoint: { nodeId, element }, direction };
}

/** Keep dragging local; submit one validated graph edit when the pointer is released. */
export function useTerminalDrag(graph: Graph, container: RefObject<HTMLDivElement | null>, terminals: Map<string, HTMLElement>, zoom: number) {
  const [preview, setPreview] = useState("");
  const active = useRef<{ key: string; anchor: Point; forward: boolean; start: Point; edge?: Connection } | null>(null);
  const point = useCallback((x: number, y: number) => {
    const rect = container.current!.getBoundingClientRect();
    return { x: (x - rect.left) / zoom, y: (y - rect.top) / zoom };
  }, [container, zoom]);
  const cancel = useCallback(() => { active.current = null; setPreview(""); }, []);
  useEffect(() => { cancel(); }, [graph, zoom, cancel]);
  const move = useCallback((x: number, y: number) => {
    const drag = active.current;
    if (!drag) return;
    const cursor = point(x, y);
    setPreview(drag.forward ? connectionPath(drag.anchor, cursor) : connectionPath(cursor, drag.anchor));
  }, [point]);
  const start = useCallback((key: string, x: number, y: number) => {
    if (backend.status.connection !== "connected") return;
    const terminal = port(key);
    const edge = terminal.direction === "input" ? graph.connections.find((edge) => terminalKey(edge.target, "input") === key) : undefined;
    const anchorKey = edge ? terminalKey(edge.source, "output") : key;
    const rect = terminals.get(anchorKey)!.getBoundingClientRect();
    active.current = { key, anchor: point(rect.left + rect.width / 2, rect.top + rect.height / 2), forward: Boolean(edge) || terminal.direction === "output", start: { x, y }, edge };
    move(x, y);
  }, [graph, terminals, point, move]);
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
  return { preview, start, move, finish, cancel, disconnect };
}

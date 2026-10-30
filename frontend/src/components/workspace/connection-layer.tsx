"use client";

import { type ReactNode, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Graph } from "@/lib/backend/protocol";
import { backend } from "@/lib/backend/store";
import { useBackendStatus, useTemplateRevision } from "@/lib/backend/hooks";
import { TerminalContext, terminalKey } from "./terminal";
import { layoutGraph } from "./graph-layout";
import { isTyping } from "./shortcuts";
import { MIN_ZOOM, MAX_ZOOM, clampZoom, zoomScroll } from "./viewport";
import { useTerminalDrag } from "./use-terminal-drag";
import { connectionPath } from "./connection-path";

/** One registry and SVG for the workspace; live data frames never redraw wires. */
export function ConnectionLayer({ graph, children }: { graph: Graph; children: ReactNode }) {
  const { connections } = graph;
  const status = useBackendStatus();
  const templateRevision = useTemplateRevision();
  const container = useRef<HTMLDivElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const anchor = useRef<{ left: number; top: number } | null>(null);
  const changeZoom = useCallback((next: number, point?: { x: number; y: number }) => {
    const element = viewport.current!;
    next = clampZoom(next);
    const { x, y } = point ?? { x: element.clientWidth / 2, y: element.clientHeight / 2 };
    anchor.current = { left: zoomScroll(element.scrollLeft, x, zoom, next), top: zoomScroll(element.scrollTop, y, zoom, next) };
    setZoom(next);
  }, [zoom]);
  useLayoutEffect(() => {
    if (anchor.current) { viewport.current!.scrollTo(anchor.current); anchor.current = null; }
  }, [zoom]);
  useEffect(() => {
    const element = viewport.current!;
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      changeZoom(zoom * Math.exp(-event.deltaY * 0.01), { x: event.clientX - rect.left, y: event.clientY - rect.top });
    };
    const key = (event: KeyboardEvent) => {
      if (isTyping() || document.querySelector("dialog[open]") || !(event.metaKey || event.ctrlKey)) return;
      if (["+", "=", "-", "0"].includes(event.key)) {
        event.preventDefault();
        changeZoom(event.key === "0" ? 1 : zoom * (event.key === "-" ? 1 / 1.2 : 1.2));
      }
    };
    element.addEventListener("wheel", wheel, { passive: false });
    window.addEventListener("keydown", key);
    return () => { element.removeEventListener("wheel", wheel); window.removeEventListener("keydown", key); };
  }, [zoom, changeZoom]);
  const terminals = useRef(new Map<string, HTMLElement>());
  const { preview, start, move, finish, cancel, disconnect } = useTerminalDrag(graph, container, terminals.current, zoom);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => { if (selected && !connections.some((edge) => edge.id === selected)) setSelected(null); }, [connections, selected]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") { cancel(); setSelected(null); }
      if (!selected || isTyping() || document.querySelector("dialog[open]")) return;
      if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault(); setSelected(null);
        void backend.command("connection.remove", { connectionId: selected });
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [selected, cancel]);
  const frame = useRef(0);
  const [paths, setPaths] = useState<{ id: string; label: string; d: string }[]>([]);
  const [layout, setLayout] = useState(0);
  const [extent, setExtent] = useState({ width: 0, height: 192 });
  const [arranging, setArranging] = useState(false);
  const autoArranged = useRef("");
  const automaticKey = JSON.stringify([templateRevision, graph.nodes.map((node) => node.id), connections]);
  const arrange = useCallback(async (recordHistory = true) => {
    const sizes = new Map([...container.current!.querySelectorAll<HTMLElement>("[data-node-id]")].map((node) => [node.dataset.nodeId!, { width: node.offsetWidth, height: node.offsetHeight }]));
    setArranging(true);
    try { await backend.command("graph.move", { positions: layoutGraph(graph, sizes), recordHistory }); }
    finally { setArranging(false); }
  }, [graph]);
  useLayoutEffect(() => {
    if (status.connection === "connected" && graph.nodes.length > 1 && graph.nodes.every((node) => node.position.every((coordinate) => coordinate === 0)) && autoArranged.current !== automaticKey) {
      autoArranged.current = automaticKey;
      void arrange(false);
    }
  }, [graph, arrange, status.connection, automaticKey]);
  const invalidate = useCallback(() => {
    if (!frame.current) frame.current = requestAnimationFrame(() => { frame.current = 0; setLayout((value) => value + 1); });
  }, []);
  const register = useCallback((key: string, element: HTMLElement) => {
    terminals.current.set(key, element);
    invalidate();
    return () => { terminals.current.delete(key); invalidate(); };
  }, [invalidate]);
  const registry = useMemo(() => ({ register, invalidate, zoom, start, move, finish, cancel, disconnect, linked: new Set(connections.flatMap((edge) => [
    terminalKey(edge.source, "output"), terminalKey(edge.target, "input"),
  ])) }), [connections, register, invalidate, zoom, start, move, finish, cancel, disconnect]);

  useLayoutEffect(() => {
    const origin = container.current!.getBoundingClientRect();
    const nodes = [...container.current!.querySelectorAll<HTMLElement>("[data-node-id]")].map((node) => node.getBoundingClientRect());
    setExtent({ width: Math.ceil(Math.max(0, ...nodes.map((node) => (node.right - origin.left) / zoom + 24))), height: Math.ceil(Math.max(192, ...nodes.map((node) => (node.bottom - origin.top) / zoom + 24))) });
    setPaths(connections.flatMap((edge) => {
      const source = terminals.current.get(terminalKey(edge.source, "output"));
      const target = terminals.current.get(terminalKey(edge.target, "input"));
      if (!source || !target) return [];
      const from = source.getBoundingClientRect(), to = target.getBoundingClientRect();
      const x1 = (from.left + from.width / 2 - origin.left) / zoom, y1 = (from.top + from.height / 2 - origin.top) / zoom;
      const x2 = (to.left + to.width / 2 - origin.left) / zoom, y2 = (to.top + to.height / 2 - origin.top) / zoom;
      return [{ id: edge.id, label: `${edge.source.nodeId}.${edge.source.element} → ${edge.target.nodeId}.${edge.target.element}`,
        d: connectionPath({ x: x1, y: y1 }, { x: x2, y: y2 }) }];
    }));
  }, [connections, layout, zoom]);
  useLayoutEffect(() => {
    const observer = new ResizeObserver(invalidate);
    observer.observe(container.current!);
    return () => { observer.disconnect(); cancelAnimationFrame(frame.current); frame.current = 0; };
  }, [invalidate]);
  return <TerminalContext.Provider value={registry}>
    <div className="flex items-center gap-3"><button type="button" disabled={arranging || !graph.nodes.length || status.connection !== "connected"} onClick={() => { void arrange(); }} className="rounded border border-white/10 px-3 py-2 text-xs text-zinc-300 hover:bg-white/5 disabled:opacity-40">{arranging ? "Arranging…" : "Arrange nodes"}</button>
      <div role="group" aria-label="Workspace zoom" className="flex items-center rounded border border-white/10 text-xs text-zinc-300">
        <button type="button" aria-label="Zoom out" disabled={zoom <= MIN_ZOOM} onClick={() => changeZoom(zoom / 1.2)} className="px-3 py-2 disabled:opacity-30">−</button>
        <button type="button" aria-label="Reset zoom" onClick={() => changeZoom(1)} className="w-14 py-2 font-mono text-[10px]">{Math.round(zoom * 100)}%</button>
        <button type="button" aria-label="Zoom in" disabled={zoom >= MAX_ZOOM} onClick={() => changeZoom(zoom * 1.2)} className="px-3 py-2 disabled:opacity-30">+</button>
      </div>
    </div>
    <p className="text-[10px] text-zinc-500">Drag terminals to connect · Drag a connected input into empty space to unlink · Select a wire and press Delete to remove it</p>
    <div ref={viewport} onPointerDown={() => setSelected(null)} className="node-canvas max-h-[75vh] min-h-48 overflow-auto rounded-xl border border-white/5">
    <div style={{ width: extent.width * zoom, height: extent.height * zoom }} className="overflow-hidden">
    <div ref={container} style={{ ...extent, transform: `scale(${zoom})`, transformOrigin: "0 0" }} className="relative min-h-48">
      <svg aria-label="Node connections" className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" fill="none">
        {paths.map((path) => <g key={path.id}>
          <path d={path.d} stroke={selected === path.id ? "#e9d5ff" : "#a78bfa"} strokeWidth={selected === path.id ? 3 : 2} strokeOpacity={0.8} />
          <path d={path.d} stroke="transparent" strokeWidth={12} pointerEvents="stroke" className="cursor-pointer"
            onPointerDown={(event) => { event.stopPropagation(); setSelected(path.id); }}><title>{path.label} · Delete to disconnect</title></path>
        </g>)}
        {preview && <path d={preview} stroke="#c4b5fd" strokeWidth={2} strokeDasharray="5 4" />}
      </svg>
      {children}
    </div>
    </div>
    </div>
  </TerminalContext.Provider>;
}

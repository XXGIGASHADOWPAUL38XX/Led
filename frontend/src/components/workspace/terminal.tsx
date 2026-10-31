"use client";

import { createContext, useCallback, useContext, useRef } from "react";
import type { Endpoint } from "@/lib/backend/protocol";
import type { CanvasDrag } from "./use-canvas-viewport";
import type { NodeMovement } from "./use-node-movement";
import { useObjectSelection } from "./object-selection";
import { terminalKey } from "./terminal-compatibility";
export { terminalKey } from "./terminal-compatibility";

export const TerminalContext = createContext<CanvasDrag & NodeMovement & {
  compatible: ReadonlySet<string> | null;
  dragging: string | null;
  linked: ReadonlySet<string>;
  register: (key: string, element: HTMLElement) => () => void;
  invalidate: () => void;
  zoom: number;
  start: (key: string, x: number, y: number) => void;
  move: (x: number, y: number) => void;
  finish: (x: number, y: number) => void;
  cancel: () => void;
  disconnect: (key: string) => void;
} | null>(null);

export function Terminal({ endpoint, direction, className = "" }: {
  endpoint?: Endpoint; direction: "input" | "output"; className?: string;
}) {
  const registry = useContext(TerminalContext);
  const selection = useObjectSelection();
  const selecting = useRef(false);
  const key = endpoint ? terminalKey(endpoint, direction) : undefined;
  const register = registry?.register;
  const ref = useCallback((element: HTMLSpanElement | null) => {
    if (element && key && register) return register(key, element);
  }, [key, register]);
  const linked = Boolean(key && registry?.linked.has(key));
  const selected = Boolean(key && selection?.value.kind === "terminal" && selection.value.ids.has(key));
  const compatible = key && registry?.compatible && registry.dragging !== key ? registry.compatible.has(key) : undefined;
  const label = `${endpoint ? `${endpoint.nodeId}.${endpoint.element} ` : ""}${direction}${linked ? " · connected" : ""}`;
  return <span ref={ref} data-terminal={key} data-linked={linked || undefined} data-selected={selected || undefined} data-compatible={compatible} role="button" aria-pressed={selected} tabIndex={key && registry ? 0 : -1} aria-label={label} title={`${label}${compatible ? " · Compatible connection" : ""} · Drag to connect · Ctrl-click to select several · Delete to disconnect`}
    onPointerDown={(event) => {
      if (!key || !registry || (event.button !== 0 && !event.ctrlKey)) return;
      event.preventDefault(); event.stopPropagation();
      selection?.select("terminal", key, event.ctrlKey || event.metaKey);
      selecting.current = true;
      event.currentTarget.focus({ preventScroll: true });
      selecting.current = false;
      if (event.ctrlKey || event.metaKey) return;
      event.currentTarget.setPointerCapture(event.pointerId);
      registry.start(key, event.clientX, event.clientY);
    }}
    onFocus={() => { if (key && !selecting.current) selection?.focus("terminal", key); }}
    onContextMenu={(event) => { if (event.ctrlKey) event.preventDefault(); }}
    onPointerMove={(event) => { if (event.currentTarget.hasPointerCapture(event.pointerId)) registry?.move(event.clientX, event.clientY); }}
    onPointerUp={(event) => {
      if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
      registry?.finish(event.clientX, event.clientY);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }}
    onPointerCancel={() => registry?.cancel()} onLostPointerCapture={() => registry?.cancel()}
    onKeyDown={(event) => { if (key && (event.key === "Delete" || event.key === "Backspace")) { event.preventDefault(); event.stopPropagation(); registry?.disconnect(key); } }}
    className={`group/terminal z-10 inline-block h-3 w-3 shrink-0 touch-none cursor-crosshair rounded-full border-2 outline-none focus-visible:ring-2 focus-visible:ring-white/70 data-[selected]:ring-2 data-[selected]:ring-white/80 data-[compatible=true]:ring-4 data-[compatible=true]:ring-emerald-400/60 data-[compatible=false]:opacity-25 ${direction === "input" ? "border-sky-400 data-[linked]:bg-sky-400" : "border-violet-400 data-[linked]:bg-violet-400"} bg-[#1c1d26] ${className}`}>
    <span aria-hidden="true" className="relative block h-full w-full"><span className="absolute -inset-2 rounded-full transition-colors hover:bg-violet-400/20 group-focus/terminal:bg-violet-400/15 group-focus/terminal:ring-2 group-focus/terminal:ring-violet-300/60" /></span>
  </span>;
}

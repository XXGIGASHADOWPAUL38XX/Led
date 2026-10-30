"use client";

import { createContext, useCallback, useContext } from "react";
import type { Endpoint } from "@/lib/backend/protocol";

export const terminalKey = (endpoint: Endpoint, direction: "input" | "output") => JSON.stringify([endpoint.nodeId, endpoint.element, direction]);
export const TerminalContext = createContext<{
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
  const key = endpoint ? terminalKey(endpoint, direction) : undefined;
  const register = registry?.register;
  const ref = useCallback((element: HTMLSpanElement | null) => {
    if (element && key && register) return register(key, element);
  }, [key, register]);
  const linked = Boolean(key && registry?.linked.has(key));
  const label = `${endpoint ? `${endpoint.nodeId}.${endpoint.element} ` : ""}${direction}${linked ? " · connected" : ""}`;
  return <span ref={ref} data-terminal={key} data-linked={linked || undefined} role="button" tabIndex={key && registry ? 0 : -1} aria-label={label} title={`${label} · Drag to connect · Delete to disconnect`}
    onPointerDown={(event) => {
      if (!key || !registry) return;
      event.preventDefault(); event.stopPropagation();
      event.currentTarget.focus({ preventScroll: true });
      event.currentTarget.setPointerCapture(event.pointerId);
      registry.start(key, event.clientX, event.clientY);
    }}
    onPointerMove={(event) => { if (event.currentTarget.hasPointerCapture(event.pointerId)) registry?.move(event.clientX, event.clientY); }}
    onPointerUp={(event) => {
      if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
      registry?.finish(event.clientX, event.clientY);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }}
    onPointerCancel={() => registry?.cancel()} onLostPointerCapture={() => registry?.cancel()}
    onKeyDown={(event) => { if (key && (event.key === "Delete" || event.key === "Backspace")) { event.preventDefault(); event.stopPropagation(); registry?.disconnect(key); } }}
    className={`z-10 inline-block h-3 w-3 shrink-0 touch-none cursor-crosshair rounded-full border-2 outline-none focus-visible:ring-2 focus-visible:ring-white/60 ${direction === "input" ? "border-sky-400 data-[linked]:bg-sky-400" : "border-violet-400 data-[linked]:bg-violet-400"} bg-[#1c1d26] ${className}`} />;
}

"use client";

import { createContext, useCallback, useContext } from "react";
import type { Endpoint } from "@/lib/backend/protocol";

export const terminalKey = (endpoint: Endpoint, direction: "input" | "output") => JSON.stringify([endpoint.nodeId, endpoint.element, direction]);
export const TerminalContext = createContext<{
  linked: ReadonlySet<string>;
  register: (key: string, element: HTMLElement) => () => void;
  invalidate: () => void;
  zoom: number;
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
  return <span ref={ref} data-terminal={key} data-linked={linked || undefined} role="img" aria-label={label} title={label}
    className={`z-10 inline-block h-3 w-3 shrink-0 rounded-full border-2 ${direction === "input" ? "border-sky-400 data-[linked]:bg-sky-400" : "border-violet-400 data-[linked]:bg-violet-400"} bg-[#1c1d26] ${className}`} />;
}

"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Graph } from "@/lib/backend/protocol";
import { backend } from "@/lib/backend/store";

export type ObjectKind = "node" | "terminal" | "wire";
export type ObjectSelection = { kind: ObjectKind | null; ids: ReadonlySet<string> };
export const emptySelection: ObjectSelection = { kind: null, ids: new Set() };
export function selectObject(previous: ObjectSelection, kind: ObjectKind, id: string, extend: boolean): ObjectSelection {
  const ids = new Set(extend && previous.kind === kind ? previous.ids : []);
  if (extend && ids.has(id)) ids.delete(id); else ids.add(id);
  return ids.size ? { kind, ids } : emptySelection;
}

type SelectionContext = {
  value: ObjectSelection;
  select: (kind: ObjectKind, id: string, extend?: boolean) => void;
  focus: (kind: ObjectKind, id: string) => void;
  clear: () => void;
};
const Context = createContext<SelectionContext | null>(null);
export const useObjectSelection = () => useContext(Context);

/** Selection stays local to the workspace; keyboard focus remains on one DOM element. */
export function ObjectSelectionProvider({ children, graph, revision }: { children: ReactNode; graph: Graph; revision: number }) {
  const [value, setValue] = useState(emptySelection);
  const select = useCallback((kind: ObjectKind, id: string, extend = false) => setValue((previous) => selectObject(previous, kind, id, extend)), []);
  const focus = useCallback((kind: ObjectKind, id: string) => setValue((previous) => previous.kind === kind && previous.ids.has(id) ? previous : selectObject(previous, kind, id, false)), []);
  const clear = useCallback(() => setValue(emptySelection), []);
  useEffect(clear, [clear, revision]);
  useEffect(() => {
    setValue((previous) => {
      const ids = new Set([...previous.ids].filter((id) => {
        if (previous.kind === "node") return graph.nodes.some((node) => node.id === id);
        if (previous.kind === "wire") return graph.connections.some((edge) => edge.id === id);
        const [nodeId, name] = JSON.parse(id) as [string, string];
        return backend.node(nodeId)?.ports.some((port) => port.name === name);
      }));
      return ids.size === previous.ids.size ? previous : ids.size ? { ...previous, ids } : emptySelection;
    });
  }, [graph]);
  const context = useMemo(() => ({ value, select, focus, clear }), [value, select, focus, clear]);
  return <Context.Provider value={context}>{children}</Context.Provider>;
}

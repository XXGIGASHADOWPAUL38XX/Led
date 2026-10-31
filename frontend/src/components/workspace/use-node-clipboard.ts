import { useEffect, useRef } from "react";
import { backend } from "@/lib/backend/store";
import type { Graph } from "@/lib/backend/protocol";
import { useObjectSelection } from "./object-selection";
import { isTyping } from "./shortcuts";

export function useNodeClipboard(insertionPosition: () => [number, number]) {
  const selection = useObjectSelection()!;
  const clipboard = useRef<Promise<Graph | null> | null>(null);
  const offset = useRef(0);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || isTyping() || document.querySelector('dialog[open], [role="listbox"]') || backend.status.connection !== "connected") return;
      if (event.key.toLowerCase() === "c" && selection.value.kind === "node" && selection.value.ids.size) {
        event.preventDefault();
        offset.current = 0;
        clipboard.current = backend.command("graph.copy", { nodeIds: [...selection.value.ids] }).then((result) => result ? (result as { graph: Graph }).graph : null);
      }
      if (event.key.toLowerCase() === "v" && clipboard.current) {
        event.preventDefault();
        offset.current++;
        const position = insertionPosition().map((coordinate) => coordinate + 24 * offset.current);
        void clipboard.current.then(async (graph) => {
          if (!graph) return;
          const result = await backend.command("graph.paste", { graph, position }) as { nodeIds: string[] } | undefined;
          if (result) selection.setNodes(result.nodeIds);
        });
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [selection, insertionPosition]);
}

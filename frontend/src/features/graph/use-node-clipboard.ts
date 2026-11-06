import { useEffect, useRef } from "react";
import { useBackend } from "@/api/backend-context";
import type { Graph } from "@/api/protocol";
import { isDialogOpen, isTyping } from "./shortcuts";

export function useNodeClipboard(
  insertionPosition: () => [number, number],
  selected: () => string[],
  select: (ids: string[]) => void,
) {
  const backend = useBackend();
  const clipboard = useRef<Promise<Graph | null> | null>(null);
  const offset = useRef(0);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (
        !(event.metaKey || event.ctrlKey) ||
        isTyping() ||
        isDialogOpen() ||
        document.querySelector('[role="listbox"]') ||
        backend.status.connection !== "connected"
      )
        return;
      const nodeIds = selected();
      if (event.key.toLowerCase() === "c" && nodeIds.length) {
        event.preventDefault();
        offset.current = 0;
        // openapi-fetch widens the schema's [x, y] position tuples to number[]; the backend validated them.
        clipboard.current = backend.graph.copy(nodeIds).then((result) => (result ? (result.graph as Graph) : null));
      }
      if (event.key.toLowerCase() === "v" && clipboard.current) {
        event.preventDefault();
        offset.current++;
        const [x, y] = insertionPosition();
        const position: [number, number] = [x + 24 * offset.current, y + 24 * offset.current];
        void clipboard.current.then(async (graph) => {
          if (!graph) return;
          const result = await backend.graph.paste(graph, position);
          if (result) select(result.nodeIds);
        });
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [backend, insertionPosition, selected, select]);
}

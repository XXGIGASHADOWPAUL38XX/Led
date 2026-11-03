import { useEffect, useRef } from "react";
import { useBackend } from "@/api/backend-context";
import type { Graph } from "@/api/protocol";
import { isTyping } from "./shortcuts";

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
        document.querySelector('dialog[open], [role="listbox"]') ||
        backend.status.connection !== "connected"
      )
        return;
      const nodeIds = selected();
      if (event.key.toLowerCase() === "c" && nodeIds.length) {
        event.preventDefault();
        offset.current = 0;
        clipboard.current = backend
          .command("graph.copy", { nodeIds })
          .then((result) => (result ? (result as { graph: Graph }).graph : null));
      }
      if (event.key.toLowerCase() === "v" && clipboard.current) {
        event.preventDefault();
        offset.current++;
        const position = insertionPosition().map((coordinate) => coordinate + 24 * offset.current);
        void clipboard.current.then(async (graph) => {
          if (!graph) return;
          const result = (await backend.command("graph.paste", { graph, position })) as
            { nodeIds: string[] } | undefined;
          if (result) select(result.nodeIds);
        });
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [backend, insertionPosition, selected, select]);
}

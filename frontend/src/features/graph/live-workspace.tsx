import { useEffect, useRef, useState } from "react";
import { useBackend } from "@/api/backend-context";
import { useBackendStatus, useGraph, useGraphEpoch } from "@/api/hooks";
import { SelectElement } from "../nodes/elements";
import { ReactFlowProvider } from "@xyflow/react";
import { compatiblePorts } from "../nodes/configuration";
import { TemplateControls } from "../templates/template-controls";
import { JevControls } from "../generation/jev-controls";
import { WorkspaceCanvas, type CanvasHandle } from "./workspace-canvas";
import { AddNodeDialog } from "../nodes/add-node-dialog";
import { isTyping } from "./shortcuts";
import { CatalogContext } from "../catalog/catalog-context";
import { useCatalogQuery } from "../catalog/use-catalog-query";

export function LiveWorkspace() {
  const backend = useBackend();
  const status = useBackendStatus();
  const snapshot = useGraph();
  const graphEpoch = useGraphEpoch();
  const catalog = useCatalogQuery();
  const canvas = useRef<CanvasHandle>(null);
  const [adding, setAdding] = useState<[number, number] | null>(null);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  useEffect(() => {
    const begin = () => backend.beginAction();
    const key = (event: KeyboardEvent) => {
      begin();
      if (document.querySelector("dialog[open]")) return;
      if (event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "a") {
        event.preventDefault();
        if (backend.status.connection === "connected") setAdding(canvas.current!.insertionPosition());
        return;
      }
      if (isTyping()) return;
      if (event.metaKey && !event.shiftKey && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (backend.status.canUndo) void backend.graph.undo();
      }
    };
    window.addEventListener("pointerdown", begin, true);
    window.addEventListener("keydown", key, true);
    return () => {
      window.removeEventListener("pointerdown", begin, true);
      window.removeEventListener("keydown", key, true);
    };
  }, [backend]);
  const outputs = (snapshot?.nodes ?? []).flatMap((node) =>
    node.ports
      .filter((port) => port.direction === "out")
      .map((port) => ({
        value: JSON.stringify({ nodeId: node.id, element: port.name }),
        label: `${node.id}.${port.name}`,
      })),
  );
  const selectedSource = source ? (JSON.parse(source) as { nodeId: string; element: string }) : null;
  const sourcePort = snapshot?.nodes
    .find((node) => node.id === selectedSource?.nodeId)
    ?.ports.find((port) => port.name === selectedSource?.element);
  const inputs = (snapshot?.nodes ?? [])
    .filter((node) => node.id !== selectedSource?.nodeId)
    .flatMap((node) =>
      node.ports
        .filter((port) => port.direction === "in" && (!sourcePort || compatiblePorts(sourcePort, port)))
        .map((port) => ({
          value: JSON.stringify({ nodeId: node.id, element: port.name }),
          label: `${node.id}.${port.name}`,
        })),
    );
  return (
    <CatalogContext value={catalog ?? null}>
      <section aria-label="Live backend workspace" className="space-y-5 border-b border-border p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-medium">Live workspace</h2>
            <p role="status" className="mt-1 text-xs text-muted-foreground">
              {status.connection} · revision {status.revision} · 50 ms frames
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={status.connection !== "connected" || !status.canUndo}
              onClick={() => {
                void backend.graph.undo();
              }}
              className="rounded border border-border px-3 py-2 text-xs text-zinc-300 disabled:opacity-40"
            >
              Undo ⌘Z
            </button>
            <button
              type="button"
              disabled={status.connection !== "connected"}
              onClick={() => setAdding(canvas.current!.insertionPosition())}
              className="rounded bg-violet-400/15 px-3 py-2 text-xs text-violet-200 disabled:opacity-40"
            >
              Add node ⌃A
            </button>
          </div>
        </div>
        <TemplateControls />
        <JevControls />
        {adding && catalog && <AddNodeDialog position={adding} onClose={() => setAdding(null)} />}
        {status.connection !== "connected" && (
          <p className="text-xs text-muted-foreground">
            Start Python with <code>.venv/bin/python -m backend.api.server</code>.
          </p>
        )}
        {status.error && (
          <p role="alert" className="rounded border border-rose-400/20 bg-rose-400/5 p-3 text-xs text-rose-300">
            {status.error}
          </p>
        )}
        {snapshot && (
          <details className="rounded border border-border p-3">
            <summary className="cursor-pointer text-xs text-zinc-400">
              Connections ({snapshot.graph.connections.length})
            </summary>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <SelectElement
                label="From"
                value={source}
                onValueChange={(value) => {
                  setSource(value);
                  setTarget("");
                }}
                options={outputs}
              />
              <SelectElement label="To" value={target} onValueChange={setTarget} options={inputs} />
              <button
                type="button"
                disabled={!source || !inputs.some((input) => input.value === target)}
                onClick={() => {
                  void backend.graph.connect(JSON.parse(source), JSON.parse(target));
                }}
                className="rounded bg-violet-400/15 py-2 text-xs text-violet-200 disabled:opacity-30"
              >
                Connect
              </button>
            </div>
            {snapshot.graph.connections.map((edge) => (
              <div key={edge.id} className="mt-2 flex justify-between gap-2 text-xs text-zinc-400">
                <span>
                  {edge.source.nodeId}.{edge.source.element} → {edge.target.nodeId}.{edge.target.element}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    void backend.graph.disconnect(edge.id);
                  }}
                  className="text-rose-300"
                >
                  Disconnect
                </button>
              </div>
            ))}
          </details>
        )}
        {snapshot && catalog && (
          // A new graph (loaded template, generated graph, reconnection) starts a fresh canvas: node state,
          // selection, viewport and automatic layout.
          <ReactFlowProvider key={graphEpoch}>
            <WorkspaceCanvas ref={canvas} graph={snapshot.graph} />
          </ReactFlowProvider>
        )}
      </section>
    </CatalogContext>
  );
}

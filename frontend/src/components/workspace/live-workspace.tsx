"use client";

import { useEffect, useState } from "react";
import { backend } from "@/lib/backend/store";
import { useBackendStatus, useGraph, useTemplateRevision } from "@/lib/backend/hooks";
import { SelectElement } from "../elements";
import { LiveNode } from "../node/live-node";
import { nodeDefinitions } from "../node/registry";
import { compatiblePorts } from "../../lib/nodes/configuration";
import { TemplateControls } from "../templates/template-controls";
import { ConnectionLayer } from "./connection-layer";
import { AddNodeDialog } from "../dialogs/add-node-dialog";
import { isTyping } from "./shortcuts";

export function LiveWorkspace() {
  const status = useBackendStatus();
  const snapshot = useGraph();
  const templateRevision = useTemplateRevision();
  const [adding, setAdding] = useState(false);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  useEffect(() => { backend.connection.start(); return () => backend.connection.stop(); }, []);
  useEffect(() => {
    const begin = () => backend.beginAction();
    const key = (event: KeyboardEvent) => {
      begin();
      if (document.querySelector("dialog[open]")) return;
      if (event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "a") { event.preventDefault(); if (backend.status.connection === "connected") setAdding(true); return; }
      if (isTyping()) return;
      if (event.metaKey && !event.shiftKey && event.key.toLowerCase() === "z") { event.preventDefault(); if (backend.status.canUndo) void backend.command("graph.undo"); }
    };
    window.addEventListener("pointerdown", begin, true);
    window.addEventListener("keydown", key, true);
    return () => { window.removeEventListener("pointerdown", begin, true); window.removeEventListener("keydown", key, true); };
  }, []);
  const outputs = (snapshot?.nodes ?? []).flatMap((node) => node.ports.filter((port) => port.direction === "out").map((port) => ({ value: JSON.stringify({ nodeId: node.id, element: port.name }), label: `${node.id}.${port.name}` })));
  const selectedSource = source ? JSON.parse(source) as { nodeId: string; element: string } : null;
  const sourcePort = snapshot?.nodes.find((node) => node.id === selectedSource?.nodeId)?.ports.find((port) => port.name === selectedSource?.element);
  const inputs = (snapshot?.nodes ?? []).filter((node) => node.id !== selectedSource?.nodeId).flatMap((node) => node.ports.filter((port) => port.direction === "in" && (!sourcePort || compatiblePorts(sourcePort, port))).map((port) => ({ value: JSON.stringify({ nodeId: node.id, element: port.name }), label: `${node.id}.${port.name}` })));
  return <section aria-label="Live backend workspace" className="space-y-5 border-b border-white/10 p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-sm font-medium">Live workspace</h2><p role="status" className="mt-1 text-xs text-zinc-500">{status.connection} · revision {status.revision} · 50 ms frames</p></div>
      <div className="flex items-center gap-2"><button type="button" disabled={status.connection !== "connected" || !status.canUndo} onClick={() => { void backend.command("graph.undo"); }} className="rounded border border-white/10 px-3 py-2 text-xs text-zinc-300 disabled:opacity-40">Undo ⌘Z</button>
        <button type="button" disabled={status.connection !== "connected"} onClick={() => setAdding(true)} className="rounded bg-violet-400/15 px-3 py-2 text-xs text-violet-200 disabled:opacity-40">Add node ⌃A</button></div>
    </div>
    <TemplateControls />
    {adding && <AddNodeDialog onClose={() => setAdding(false)} />}
    {status.connection !== "connected" && <p className="text-xs text-zinc-500">Start Python with <code>.venv/bin/python -m backend.api.server</code>. Component previews below work offline.</p>}
    {status.error && <p role="alert" className="rounded border border-rose-400/20 bg-rose-400/5 p-3 text-xs text-rose-300">{status.error}</p>}
    {snapshot && <details className="rounded border border-white/10 p-3"><summary className="cursor-pointer text-xs text-zinc-400">Connections ({snapshot.graph.connections.length})</summary>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <SelectElement label="From" value={source} onValueChange={(value) => { setSource(value); setTarget(""); }} options={outputs} />
        <SelectElement label="To" value={target} onValueChange={setTarget} options={inputs} />
        <button type="button" disabled={!source || !inputs.some((input) => input.value === target)} onClick={() => { void backend.command("connection.add", { source: JSON.parse(source), target: JSON.parse(target) }); }} className="rounded bg-violet-400/15 py-2 text-xs text-violet-200 disabled:opacity-30">Connect</button>
      </div>
      {snapshot.graph.connections.map((edge) => <div key={edge.id} className="mt-2 flex justify-between gap-2 text-xs text-zinc-400"><span>{edge.source.nodeId}.{edge.source.element} → {edge.target.nodeId}.{edge.target.element}</span>
        <button type="button" onClick={() => { void backend.command("connection.remove", { connectionId: edge.id }); }} className="text-rose-300">Disconnect</button></div>)}
    </details>}
    {snapshot && <ConnectionLayer graph={snapshot.graph}>{snapshot.graph.nodes.map((node) => <LiveNode key={`${templateRevision}:${node.id}`} id={node.id} />)}</ConnectionLayer>}
  </section>;
}

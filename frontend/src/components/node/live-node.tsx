"use client";

import { backend } from "@/lib/backend/store";
import { useBackendNode, useGraph } from "@/lib/backend/hooks";
import { Node } from "./node";
import { NodeFields } from "./node-fields";
import { NodeView } from "./node-views";
import { nodeDefinitions } from "./registry";

export function LiveNode({ id }: { id: string }) {
  const node = useBackendNode(id);
  const snapshot = useGraph();
  if (!node) return null;
  const definition = nodeDefinitions[node.type];
  if (!definition) return <p role="alert">Missing UI definition for {node.type}</p>;
  const position = snapshot?.graph.nodes.find((item) => item.id === id)?.position ?? [0, 0];
  // Dynamic stems and argument ports follow the live processing schema.
  const views = [...definition.views, ...node.ports.filter((port) => port.direction === "out" && !definition.views.some((view) => view.data === port.name))
    .map((port) => ({ kind: node.type === "StemsRecognition" ? "trigger" as const : "bars" as const, data: port.name, label: port.name, open: false }))];
  const shown = new Set([...definition.fields.map((field) => field.name), ...views.map((view) => view.data)]);
  return <Node absolute id={id} title={definition.title} description={definition.description} initialPosition={{ x: position[0], y: position[1] }}
    inputs={node.ports.filter((port) => port.direction === "in" && !shown.has(port.name)).map((port) => port.name)}
    onPositionCommit={({ x, y }) => { void backend.command("node.move", { nodeId: id, position: [x, y] }); }}>
    <div className="flex items-center justify-between text-[10px] text-zinc-500"><span>{definition.category} · {id}</span>
      <button type="button" onClick={() => { void backend.command("node.remove", { nodeId: id }); }} aria-label={`Remove ${id}`} className="rounded px-2 py-1 text-rose-300 hover:bg-rose-400/10">Remove</button></div>
    <NodeFields key={node.id + JSON.stringify(snapshot?.graph.nodes.find((item) => item.id === id)?.parameters)} node={node} definition={definition} />
    {definition.actions && <div className="flex gap-2">{definition.actions.map((action) => <button key={action} type="button"
      onClick={() => { void backend.command(`node.${action}`, { nodeId: id }); }} className="flex-1 rounded bg-violet-400/15 py-2 text-xs capitalize text-violet-200">{action}</button>)}</div>}
    {views.map((view, index) => <NodeView key={`${view.data ?? view.kind}-${index}`} node={node} view={view} />)}
  </Node>;
}

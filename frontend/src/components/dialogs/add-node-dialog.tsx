"use client";

import { useEffect, useRef, useState } from "react";
import { backend } from "@/lib/backend/store";
import { useGraph } from "@/lib/backend/hooks";
import type { NodeDescriptor, Endpoint } from "@/lib/backend/protocol";
import { TextElement } from "../elements";
import { FieldControl, ReferenceControl } from "../forms/field-control";
import { completeConfiguration } from "../../lib/nodes/configuration";
import { nodeDefinitions } from "../node/registry";
import { availableNodeName } from "../../lib/nodes/node-name";

export function AddNodeDialog({ onClose, position }: { onClose: () => void; position: [number, number] }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const snapshot = useGraph();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [type, setType] = useState("");
  const [node, setNode] = useState<NodeDescriptor | null>(null);
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const choices = (snapshot?.catalog ?? []).filter((item) => `${item.type} ${nodeDefinitions[item.type].title} ${nodeDefinitions[item.type].category}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => nodeDefinitions[a.type].category.localeCompare(nodeDefinitions[b.type].category) || nodeDefinitions[a.type].title.localeCompare(nodeDefinitions[b.type].title));
  const folders = new Map<string, { type: string; index: number }[]>();
  choices.forEach((item, index) => {
    const folder = nodeDefinitions[item.type].category;
    if (!folders.has(folder)) folders.set(folder, []);
    folders.get(folder)!.push({ type: item.type, index });
  });
  const definition = nodeDefinitions[type];
  const automaticName = type ? availableNodeName(definition.title, snapshot?.graph.nodes.map((node) => node.id) ?? []) : "";
  useEffect(() => { dialog.current!.showModal(); search.current!.focus(); }, []);
  useEffect(() => { dialog.current?.querySelector("[data-selected=true]")?.scrollIntoView({ block: "nearest" }); }, [selected, type, query]);
  useEffect(() => {
    if (!type) return;
    let active = true;
    setNode(null); setParameters({}); setError("");
    void backend.command("node.describe", { nodeType: type }).then((result) => {
      if (active && result) setNode({ ...result as NodeDescriptor, id: "" });
    });
    return () => { active = false; };
  }, [type]);
  async function create() {
    setBusy(true); setError("");
    const nodeId = name.trim() || automaticName;
    const values = { ...parameters };
    for (const field of definition.fields.filter((field) => field.control === "shape")) {
      values[field.name] ??= node!.elements.find((element) => element.name === field.name)!.value;
    }
    const connections = definition.fields.filter((field) => field.control === "port").flatMap((field) => {
      const source = values[field.name] as Endpoint | null;
      delete values[field.name];
      return source ? [{ id: crypto.randomUUID(), source, target: { nodeId, element: field.name } }] : [];
    });
    try {
      const result = await backend.command("node.add", { nodeId, nodeType: type, parameters: values, connections, position });
      if (result) dialog.current!.close();
      else setError(backend.status.error);
    } finally { setBusy(false); }
  }
  return <dialog ref={dialog} onClose={onClose} className="m-auto max-h-[85vh] w-[min(90vw,420px)] overflow-y-auto rounded-xl border border-white/15 bg-[#1c1d26] p-5 text-zinc-200 shadow-2xl backdrop:bg-black/65">
    <div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">{type ? definition.title : "Add node"}</h2><button type="button" aria-label="Close add node" onClick={() => dialog.current!.close()} className="text-zinc-500">✕</button></div>
    {!type ? <>
      <input ref={search} aria-label="Search nodes" placeholder="Search nodes…" value={query} onChange={(event) => { setQuery(event.target.value); setSelected(0); }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); setSelected((index) => Math.max(0, Math.min(choices.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)))); }
          if (event.key === "Enter" && choices[selected]) { event.preventDefault(); setType(choices[selected].type); }
        }} className="mb-3 w-full rounded-lg border border-white/10 bg-black/20 p-3 text-sm outline-none focus:border-violet-400" />
      <div className="max-h-80 space-y-1 overflow-y-auto">{[...folders].map(([folder, items]) => <details key={folder} open={Boolean(query) || items.some((item) => item.index === selected)} className="rounded-lg border border-white/5 bg-black/10">
        <summary className="cursor-pointer px-3 py-2 text-xs text-zinc-300"><span className="ml-1 capitalize">{folder}</span><span className="ml-2 text-[10px] text-zinc-500">{items.length}</span></summary>
        <div className="space-y-0.5 px-2 pb-2">{items.map((item) => <button key={item.type} type="button" data-selected={selected === item.index} onClick={() => setType(item.type)}
          className={`block w-full rounded-md px-3 py-2 text-left text-xs ${selected === item.index ? "bg-violet-400/15 text-violet-200" : "text-zinc-400 hover:bg-white/5"}`}>
          {nodeDefinitions[item.type].title}</button>)}</div>
      </details>)}
        {!choices.length && <p className="p-3 text-xs text-zinc-500">No matching nodes.</p>}</div>
    </> : <form onSubmit={(event) => { event.preventDefault(); void create(); }} className="space-y-3">
      <p className="text-xs text-zinc-400">{definition.description}</p>
      <TextElement label="Name" value={name} onValueChange={setName} placeholder={automaticName} />
      {!node ? <p className="text-xs text-zinc-500">Loading parameters…</p> : definition.fields.filter((field) => !field.hidden && field.control !== "managed").map((field) => {
        const element = node.elements.find((item) => item.name === field.name);
        if (!element) return null;
        const value = Object.hasOwn(parameters, field.name) ? parameters[field.name] : element.value;
        const onChange = (value: unknown) => setParameters((previous) => ({ ...previous, [field.name]: value }));
        const count = field.bounds ? Number(parameters[field.bounds.from] ?? node.elements.find((item) => item.name === field.bounds!.from)?.value) : 0;
        return <div key={field.name}>{field.control === "port" ? <ReferenceControl nodeId={node.id} field={field} value={(parameters[field.name] ?? null) as Endpoint | null} onChange={onChange} />
          : <FieldControl node={node} field={field} parameters={parameters} onParametersChange={(values) => setParameters((previous) => ({ ...previous, ...values }))} element={field.bounds ? { ...element, min: Math.floor(count * field.bounds.min), max: Math.floor(count * field.bounds.max) } : element} value={value} onChange={onChange} />}</div>;
      })}
      {error && <p role="alert" className="text-xs text-rose-300">{error}</p>}
      <div className="flex justify-between gap-2 pt-2"><button type="button" disabled={busy} onClick={() => { setType(""); setName(""); }} className="text-xs text-zinc-400">Back</button>
        <button type="submit" disabled={busy || !node || !completeConfiguration(definition.fields, parameters)} className="rounded-lg bg-violet-400/20 px-4 py-2 text-xs text-violet-200 disabled:opacity-40">{busy ? "Creating…" : "Create node"}</button></div>
    </form>}
  </dialog>;
}

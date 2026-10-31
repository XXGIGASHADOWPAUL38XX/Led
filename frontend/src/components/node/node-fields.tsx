"use client";

import { useEffect, useRef, useState } from "react";
import { backend } from "@/lib/backend/store";
import { isArrayValue, type NodeDescriptor } from "@/lib/backend/protocol";
import type { NodeDefinition } from "./definition";
import { completeConfiguration } from "../../lib/nodes/configuration";
import { Terminal } from "../workspace/terminal";
import { FieldControl } from "../forms/field-control";

export function NodeFields({ node, definition }: { node: NodeDescriptor; definition: NodeDefinition }) {
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const changes = useRef(draft);
  const pending = useRef(false);
  useEffect(() => { changes.current = {}; setDraft({}); }, [node]);
  const complete = completeConfiguration(definition.fields, draft);
  async function commit() {
    const parameters = changes.current;
    if (pending.current || !Object.keys(parameters).length || !completeConfiguration(definition.fields, parameters)) return;
    pending.current = true;
    setSaving(true);
    try {
      const structural = definition.fields.some((field) => Object.hasOwn(parameters, field.name) && (field.rebuild || field.bounds || ["sequence", "expression", "node-reference", "curve", "axis"].includes(field.control)));
      const result = structural
        ? await backend.command("node.configure", { nodeId: node.id, parameters })
        : await Promise.all(Object.entries(parameters).map(([name, value]) => backend.setElement(node.id, name, value)));
      if (result !== undefined) { changes.current = {}; setDraft({}); setError(""); }
      else setError(backend.status.error ?? "Could not apply changes");
    } finally { pending.current = false; setSaving(false); }
  }
  return <div className="space-y-2">
    {definition.fields.filter((field) => !field.hidden && (field.control !== "port" || !definition.views.some((view) => view.data === field.name))).map((field) => {
      const element = node.elements.find((element) => element.name === field.name);
      if (!element) return null;
      const count = field.bounds ? Number(draft[field.bounds.from] ?? node.elements.find((item) => item.name === field.bounds!.from)?.value) : 0;
      const constrained = field.bounds ? { ...element, min: Math.floor(count * field.bounds.min), max: Math.floor(count * field.bounds.max) } : element;
      return <div key={field.name} data-node-field={field.name} className="relative">
      {field.control !== "port" && (field.control === "color" || !(element.disabled && isArrayValue(element.value))) && node.ports.some((port) => port.name === field.name && port.direction === "in") && <Terminal endpoint={{ nodeId: node.id, element: field.name }} direction="input" className="absolute -left-5 top-3" />}
      <FieldControl node={node} field={field} element={constrained} disabled={saving} parameters={draft} onParametersChange={(values) => { if (pending.current) return; const next = { ...changes.current, ...values }; changes.current = next; setDraft(next); }} onCommit={() => { void commit(); }} value={Object.hasOwn(draft, field.name) ? draft[field.name] : element.value}
        onChange={(value) => {
          if (pending.current) return;
          const next = { ...changes.current, [field.name]: value };
          for (const dependent of definition.fields.filter((item) => item.bounds?.from === field.name)) {
            const bounds = dependent.bounds!;
            const current = Number(next[dependent.name] ?? node.elements.find((item) => item.name === dependent.name)?.value);
            next[dependent.name] = Math.max(Math.floor(Number(value) * bounds.min), Math.min(Math.floor(Number(value) * bounds.max), current));
          }
          changes.current = next;
          setDraft(next);
        }} /></div>;
    })}
    {error && <p role="alert" className="text-[10px] text-rose-300">{error}</p>}
    {!complete && <p role="status" className="text-[10px] text-zinc-500">Choose a source for each reference to finish the change.</p>}
  </div>;
}

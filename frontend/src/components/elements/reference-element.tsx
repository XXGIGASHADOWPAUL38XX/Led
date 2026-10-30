"use client";

import { SelectElement } from "./select-element";

export type ElementReference = { nodeId: string; elementId: string | null };
export type ReferenceNode = { id: string; label: string; elements: readonly { id: string; label: string; disabled?: boolean }[] };
export type ReferenceElementProps = {
  label: string;
  nodes: readonly ReferenceNode[];
  value: ElementReference | null;
  onValueChange: (value: ElementReference | null) => void;
  disabled?: boolean;
};

export function ReferenceElement({ label, nodes, value, onValueChange, disabled = false }: ReferenceElementProps) {
  const node = nodes.find((item) => item.id === value?.nodeId);
  return (
    <fieldset disabled={disabled} className="space-y-1.5 rounded-lg border border-white/5 bg-black/10 p-2">
      <legend className="px-1 text-[10px] text-zinc-400">{label}</legend>
      <SelectElement label="Node" value={node?.id ?? ""} disabled={disabled} placeholder="Choose node"
        options={nodes.map((item) => ({ value: item.id, label: item.label }))}
        onValueChange={(nodeId) => onValueChange({ nodeId, elementId: null })} />
      <SelectElement label="Element" value={node?.elements.some((item) => item.id === value?.elementId) ? value?.elementId ?? "" : ""}
        disabled={disabled || !node} placeholder={node ? "Choose element" : "Select node first"}
        options={(node?.elements ?? []).map((item) => ({ value: item.id, label: item.label, disabled: item.disabled }))}
        onValueChange={(elementId) => { if (node) onValueChange({ nodeId: node.id, elementId }); }} />
      {value && <button type="button" disabled={disabled} onClick={() => onValueChange(null)} aria-label={`Clear ${label}`}
        className="block ml-auto rounded px-1.5 py-1 text-[10px] text-zinc-500 hover:bg-white/5 hover:text-zinc-200 focus-visible:outline-2 focus-visible:outline-violet-400 disabled:opacity-40">Clear</button>}
    </fieldset>
  );
}

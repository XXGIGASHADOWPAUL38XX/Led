"use client";

import type { Endpoint } from "@/lib/backend/protocol";
import { SliderElement } from "../elements";
import { Terminal } from "../workspace/terminal";
import { ReferenceControl } from "./field-control";

export type BlendInput = { source: Endpoint | number | number[] | null; weight: number };

export function BlendControl({ nodeId, value, onChange, onCommit, disabled }: {
  nodeId: string; value: BlendInput[]; onChange: (value: BlendInput[]) => void; onCommit?: () => void; disabled: boolean;
}) {
  const update = (index: number, changes: Partial<BlendInput>) => onChange(value.map((item, at) => at === index ? { ...item, ...changes } : item));
  return <fieldset disabled={disabled} className="space-y-2 disabled:opacity-40">
    {value.map((item, index) => {
      const source = item.source !== null && typeof item.source === "object" && "nodeId" in item.source ? item.source : null;
      return <div key={index} className="relative rounded-lg border border-white/10 bg-black/15 px-2 py-1.5">
        <Terminal endpoint={{ nodeId, element: `input_${index}` }} direction="input" className="absolute -left-5 top-4" />
        <div className="flex items-center gap-2 text-[10px]">
          <span className="min-w-0 flex-1 truncate text-zinc-300">{source ? `${source.nodeId} · ${source.element}` : `Input ${index + 1}`}</span>
          <button type="button" aria-label={`Remove input ${index + 1}`} onClick={() => { onChange(value.filter((_, at) => at !== index)); onCommit?.(); }} className="rounded px-1 text-xs text-zinc-500 hover:text-rose-300">×</button>
        </div>
        <SliderElement label="Weight" value={item.weight} min={0} max={10} step={0.01} disabled={disabled}
          onValueChange={(weight) => update(index, { weight })} onValueCommit={onCommit} />
        <details open={!source} className="text-[10px] text-zinc-500"><summary className="cursor-pointer">Source</summary>
          <ReferenceControl nodeId={nodeId} field={{ name: "source", label: "Source", control: "reference" }} value={source} disabled={disabled}
            onChange={(source) => { update(index, { source: source?.element ? { nodeId: source.nodeId, element: source.element } : null }); onCommit?.(); }} />
        </details>
      </div>;
    })}
    <div className="relative">
      <Terminal endpoint={{ nodeId, element: "add_element" }} direction="input" className="absolute -left-5 top-2" />
      <button type="button" onClick={() => { onChange([...value, { source: null, weight: 1 }]); onCommit?.(); }} className="w-full rounded border border-dashed border-white/10 py-2 text-[10px] text-violet-300 hover:bg-violet-400/10">+ Add input · or drop a wire</button>
    </div>
  </fieldset>;
}

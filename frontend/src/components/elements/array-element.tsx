"use client";

import { useId, useState } from "react";
import { CoreElement } from "./core-element";

import { arrayShape, parseArrayShape, parseNumericArray, type NumericArray } from "../../lib/arrays/array-values";
export type { NumericArray } from "../../lib/arrays/array-values";

export type ArrayElementProps = {
  label: string;
  value: NumericArray;
  onValueChange: (value: NumericArray) => void;
  integer?: boolean;
  min?: number;
  max?: number;
  disabled?: boolean;
  shape?: boolean;
};

export function ArrayElement({ label, value, onValueChange, integer = false, min = -Infinity, max = Infinity, disabled = false, shape = false }: ArrayElementProps) {
  const id = useId();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  function apply() {
    try {
      onValueChange(shape ? parseArrayShape(draft) : parseNumericArray(draft, value, { integer, min, max }));
      setEditing(false);
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Invalid array."); }
  }
  return <div className="space-y-1.5">
    <CoreElement id={id} label={label} disabled={disabled} error={error}>
      <button type="button" disabled={disabled} onClick={() => { setDraft(JSON.stringify(value)); setError(""); setEditing(!editing); }} aria-expanded={editing} aria-controls={`${id}-editor`}
        className="absolute inset-0 rounded-[inherit] pr-3 text-right font-mono text-[10px] text-violet-300 outline-violet-400">{(shape ? value : arrayShape(value)).join(" × ")} · Edit</button>
    </CoreElement>
    {editing && <fieldset disabled={disabled} id={`${id}-editor`} className="space-y-1.5">
      <textarea aria-label={`Edit ${label}`} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} value={draft} onChange={(event) => setDraft(event.target.value)}
        onBlur={apply} onKeyDown={(event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); apply(); } }}
        className="h-24 w-full resize-y rounded border border-white/10 bg-black/20 p-2 font-mono text-xs text-zinc-300 outline-violet-400" />
      <p className="text-[10px] text-zinc-500">Commit on blur or ⌘Enter</p>
    </fieldset>}
  </div>;
}

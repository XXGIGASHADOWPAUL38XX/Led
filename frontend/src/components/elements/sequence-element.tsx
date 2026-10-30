"use client";

import type { ReactNode } from "react";

export type SequenceElementProps<T> = {
  label: string;
  value: readonly T[];
  onValueChange: (value: T[]) => void;
  onValueCommit?: () => void;
  createItem: () => T;
  renderItem: (item: T, index: number, onChange: (value: T) => void) => ReactNode;
  disabled?: boolean;
};

export function SequenceElement<T>({ label, value, onValueChange, onValueCommit, createItem, renderItem, disabled = false }: SequenceElementProps<T>) {
  function move(index: number, offset: number) {
    const next = [...value];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    onValueChange(next);
    onValueCommit?.();
  }
  return <fieldset disabled={disabled} className="space-y-2 rounded-lg border border-white/10 bg-black/10 p-2 disabled:opacity-40">
    <legend className="px-1 text-[10px] text-zinc-400">{label}</legend>
    {value.map((item, index) => <div key={index} className="space-y-1 rounded border border-white/5 p-1.5">
      {renderItem(item, index, (next) => onValueChange(value.map((entry, at) => at === index ? next : entry)))}
      <div className="flex justify-end gap-1 text-[10px] text-zinc-500">
        <button type="button" aria-label={`Move ${label} item ${index + 1} up`} disabled={disabled || index === 0} onClick={() => move(index, -1)} className="rounded px-2 py-1 hover:bg-white/5 disabled:opacity-25">↑</button>
        <button type="button" aria-label={`Move ${label} item ${index + 1} down`} disabled={disabled || index === value.length - 1} onClick={() => move(index, 1)} className="rounded px-2 py-1 hover:bg-white/5 disabled:opacity-25">↓</button>
        <button type="button" aria-label={`Remove ${label} item ${index + 1}`} onClick={() => { onValueChange(value.filter((_, at) => at !== index)); onValueCommit?.(); }} className="rounded px-2 py-1 hover:bg-rose-400/10 hover:text-rose-300">Remove</button>
      </div>
    </div>)}
    {!value.length && <p className="px-1 text-xs text-zinc-600">No items</p>}
    <button type="button" onClick={() => { onValueChange([...value, createItem()]); onValueCommit?.(); }} className="w-full rounded border border-dashed border-white/10 py-1.5 text-[10px] text-violet-300 hover:bg-violet-400/10">+ Add item</button>
  </fieldset>;
}

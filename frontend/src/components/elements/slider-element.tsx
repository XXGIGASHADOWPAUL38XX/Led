"use client";

import * as Slider from "@radix-ui/react-slider";
import { useId, useState } from "react";
import { CoreElement } from "./core-element";

export type SliderElementProps = {
  label: string;
  value: number;
  onValueChange: (value: number) => void;
  onValueCommit?: () => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  scale?: "linear" | "logarithmic";
  disabled?: boolean;
};

export function SliderElement({ label, value, onValueChange, onValueCommit, min, max, step = 1, unit = "", scale = "linear", disabled = false }: SliderElementProps) {
  const id = useId();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const formatted = new Intl.NumberFormat("en", { maximumFractionDigits: 6 }).format(value);

  const logarithmic = scale === "logarithmic";
  const position = logarithmic ? (min === max ? 0 : Math.log(value / min) / Math.log(max / min) * 1000) : value;

  function changePosition(next: number) {
    const number = logarithmic ? min * (max / min) ** (next / 1000) : next;
    const snapped = Number((min + Math.round((number - min) / step) * step).toPrecision(12));
    onValueChange(Math.min(max, Math.max(min, snapped)));
  }

  function edit() {
    setDraft(String(value));
    setError("");
    setEditing(true);
  }

  function commit() {
    const number = Number(draft);
    if (!draft.trim() || !Number.isFinite(number)) {
      setError("Enter a valid number.");
      return;
    }
    const clamped = Math.min(max, Math.max(min, number));
    const snapped = Number((min + Math.round((clamped - min) / step) * step).toPrecision(12));
    onValueChange(Math.min(max, Math.max(min, snapped)));
    onValueCommit?.();
    setEditing(false);
    setError("");
  }

  return (
    <CoreElement id={id} label={label} disabled={disabled} error={error}>
      <Slider.Root min={logarithmic ? 0 : min} max={logarithmic ? 1000 : max} step={logarithmic ? 1 : step} value={[position]} disabled={disabled || editing}
        onValueChange={([next]) => changePosition(next)}
        onValueCommit={onValueCommit}
        className="absolute inset-0 flex touch-none select-none items-center rounded-[inherit] cursor-ew-resize">
        <Slider.Track className="relative h-full w-full overflow-hidden rounded-[inherit]">
          <Slider.Range className="absolute inset-y-0 bg-gradient-to-r from-violet-500/25 to-violet-400/45 group-hover:from-violet-500/35 group-hover:to-violet-400/55" />
        </Slider.Track>
        <Slider.Thumb aria-labelledby={`${id}-label`} aria-valuemin={min} aria-valuemax={max} aria-valuenow={value} aria-valuetext={`${formatted} ${unit}`.trim()}
          className="block h-7 w-0.5 rounded-full bg-violet-200/70 opacity-0 outline-none transition-opacity group-hover:opacity-100 focus:opacity-100" />
      </Slider.Root>
      {editing ? (
        <input id={id} aria-labelledby={`${id}-label`} aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined} inputMode="decimal" autoFocus
          value={draft} onChange={(event) => setDraft(event.target.value)} onFocus={(event) => event.target.select()}
          onBlur={commit} onKeyDown={(event) => {
            if (event.key === "Enter") commit();
            if (event.key === "Escape") { setEditing(false); setError(""); }
          }}
          className="absolute inset-y-1 right-1 z-20 w-24 rounded bg-[#14141d] px-2 text-right font-mono text-xs text-white outline-none ring-1 ring-violet-400/60" />
      ) : (
        <button type="button" disabled={disabled} aria-label={`Edit ${label} value`}
          title="Double-click to type a value" onDoubleClick={edit} onClick={(event) => { if (event.detail === 0) edit(); }}
          className="absolute inset-y-0 right-0 z-20 min-w-20 rounded-r-md px-3 text-right font-mono text-xs tabular-nums text-zinc-100 transition-colors hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-violet-300">
          {formatted}{unit && <span className="ml-1 text-zinc-400">{unit}</span>}
        </button>
      )}
    </CoreElement>
  );
}

"use client";

import * as Slider from "@radix-ui/react-slider";
import { useId } from "react";
import { CoreElement } from "./core-element";

export type IntervalElementProps = {
  label: string;
  value: readonly [number, number];
  onValueChange: (value: [number, number]) => void;
  onValueCommit?: () => void;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
};

export function IntervalElement({ label, value, onValueChange, onValueCommit, min, max, step = 0.01, disabled = false }: IntervalElementProps) {
  const id = useId();
  return (
    <fieldset disabled={disabled} aria-label={label} className="space-y-1.5">
      <CoreElement id={id} label={label} disabled={disabled}>
        <div className="absolute inset-y-0 right-2 flex items-center gap-1 font-mono text-[10px]">
          {value.map((number, index) => <input key={index} type="number" aria-label={`${label} ${index === 0 ? "minimum" : "maximum"}`}
            min={index === 0 ? min : value[0]} max={index === 0 ? value[1] : max} step={step} value={number}
            onChange={(event) => {
              if (!event.target.value || !Number.isFinite(event.target.valueAsNumber)) return;
              const next = Math.min(index === 0 ? value[1] : max, Math.max(index === 0 ? min : value[0], event.target.valueAsNumber));
              onValueChange(index === 0 ? [next, value[1]] : [value[0], next]);
            }} onBlur={onValueCommit} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); onValueCommit?.(); } }} className="w-16 rounded bg-white/5 px-1.5 py-1 text-right text-zinc-200 outline-violet-400" />)}
        </div>
      </CoreElement>
      <Slider.Root value={[...value]} min={min} max={max} step={step} disabled={disabled} onValueChange={([low, high]) => onValueChange([low, high])}
        onValueCommit={onValueCommit}
        className="relative mx-2 flex h-4 touch-none select-none items-center data-[disabled]:opacity-40">
        <Slider.Track className="relative h-1 w-full rounded-full bg-white/10"><Slider.Range className="absolute h-full rounded-full bg-violet-400/70" /></Slider.Track>
        {["minimum", "maximum"].map((end) => <Slider.Thumb key={end} aria-label={`${label} ${end} handle`}
          className="block h-2.5 w-2.5 rounded-full bg-violet-200 outline-none focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#1c1d26]" />)}
      </Slider.Root>
    </fieldset>
  );
}

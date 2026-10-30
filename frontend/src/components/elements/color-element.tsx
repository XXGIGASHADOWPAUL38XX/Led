"use client";

import { useId } from "react";
import { CoreElement } from "./core-element";
import { SliderElement } from "./slider-element";

export type Color = readonly [number, number, number] | readonly [number, number, number, number];
export type ColorElementProps = { label: string; value: Color; onValueChange: (value: Color) => void; onValueCommit?: () => void; disabled?: boolean };

export function ColorElement({ label, value, onValueChange, onValueCommit, disabled = false }: ColorElementProps) {
  const id = useId();
  const hex = `#${value.slice(0, 3).map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
  const alpha = value.length === 4 ? value[3] / 255 : 1;

  function update(channels: readonly number[]) {
    onValueChange(value.length === 4 ? [channels[0], channels[1], channels[2], channels[3]] : [channels[0], channels[1], channels[2]]);
  }

  return (
    <div className="space-y-1">
      <CoreElement id={id} label={label} disabled={disabled}>
        <span className="absolute inset-y-0 right-3 flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase text-zinc-400">{hex}{value.length === 4 ? Math.round(value[3]).toString(16).padStart(2, "0") : ""}</span>
          <span className="relative h-5 w-8 overflow-hidden rounded border border-white/20 bg-[repeating-conic-gradient(#52525b_0%_25%,#27272a_0%_50%)] bg-[length:8px_8px]">
            <span className="absolute inset-0" style={{ backgroundColor: hex, opacity: alpha }} />
            <input type="color" value={hex} disabled={disabled} aria-labelledby={`${id}-label`}
              onBlur={onValueCommit}
              onChange={(event) => {
                update([1, 3, 5].map((offset) => parseInt(event.target.value.slice(offset, offset + 2), 16)).concat(value.length === 4 ? [value[3]] : []));
                if (event.nativeEvent.type === "change") onValueCommit?.();
              }}
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0" />
          </span>
        </span>
      </CoreElement>
      <details className="rounded-md border border-white/5 bg-black/10">
        <summary className="cursor-pointer px-3 py-1.5 text-[10px] text-zinc-500 outline-violet-400">{value.length === 4 ? "RGBA" : "RGB"} channels</summary>
        <div className="space-y-1.5 p-2 pt-0">{value.map((channel, index) => (
          <SliderElement key={index} label={["Red", "Green", "Blue", "Alpha"][index]} value={channel} min={0} max={255} disabled={disabled}
            onValueChange={(next) => update(value.map((current, at) => at === index ? next : current))} onValueCommit={onValueCommit} />
        ))}</div>
      </details>
    </div>
  );
}

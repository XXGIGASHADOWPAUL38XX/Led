"use client";

import { useRef } from "react";

export type CurvePoint = readonly [number, number];
export type CurveElementProps = { label: string; value: readonly CurvePoint[]; onValueChange: (value: CurvePoint[]) => void; onValueCommit?: () => void; disabled?: boolean };

export function CurveElement({ label, value, onValueChange, onValueCommit, disabled = false }: CurveElementProps) {
  const dragging = useRef<number | null>(null);
  function update(index: number, x: number, y: number) {
    const low = index === 0 ? 0 : value[index - 1][0] + 0.001;
    const high = index === value.length - 1 ? 1 : value[index + 1][0] - 0.001;
    const nextX = index === 0 ? 0 : index === value.length - 1 ? 1 : Math.max(low, Math.min(high, x));
    onValueChange(value.map((point, at) => at === index ? [nextX, Math.max(0, Math.min(1, y))] : point));
  }
  return <fieldset disabled={disabled} className="rounded-lg border border-white/10 bg-black/20 p-2 disabled:opacity-40">
    <legend className="px-1 text-[10px] text-zinc-400">{label}</legend>
    <svg viewBox="0 0 240 120" aria-label={`${label} curve editor`} className="h-32 w-full touch-none overflow-visible rounded bg-violet-400/5"
      onPointerDown={(event) => {
        if (disabled) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        const rect = event.currentTarget.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, 1 - (event.clientY - rect.top) / rect.height));
        if (value.every((point) => Math.abs(point[0] - x) > 0.01)) onValueChange([...value, [x, y] as CurvePoint].sort((a, b) => a[0] - b[0]));
      }}
      onPointerMove={(event) => {
        if (disabled || dragging.current === null) return;
        const rect = event.currentTarget.getBoundingClientRect();
        update(dragging.current, (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
      }} onPointerUp={() => { dragging.current = null; onValueCommit?.(); }} onPointerCancel={() => { dragging.current = null; onValueCommit?.(); }}>
      {[30, 60, 90].map((y) => <path key={y} d={`M0 ${y}H240`} stroke="#ffffff0c" />)}
      <polyline points={value.map(([x, y]) => `${x * 240},${(1 - y) * 120}`).join(" ")} fill="none" stroke="#a78bfa" strokeWidth={2} />
      {value.map(([x, y], index) => <circle key={index} cx={x * 240} cy={(1 - y) * 120} r={4} fill="#ddd6fe" stroke="#7c3aed"
        role="slider" aria-label={`${label} point ${index + 1}`} aria-valuemin={0} aria-valuemax={1} aria-valuenow={y} aria-valuetext={`x ${x.toFixed(2)}, y ${y.toFixed(2)}`} aria-disabled={disabled}
        tabIndex={disabled ? -1 : 0} className="cursor-move outline-none focus:fill-white focus:stroke-white"
        onKeyUp={onValueCommit}
        onPointerDown={(event) => { event.stopPropagation(); if (!disabled) { dragging.current = index; event.currentTarget.setPointerCapture(event.pointerId); } }}
        onKeyDown={(event) => {
          if (disabled) return;
          if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
            event.preventDefault();
            update(index, x + (event.key === "ArrowRight" ? 0.01 : event.key === "ArrowLeft" ? -0.01 : 0), y + (event.key === "ArrowUp" ? 0.01 : event.key === "ArrowDown" ? -0.01 : 0));
          }
          if ((event.key === "Delete" || event.key === "Backspace") && index > 0 && index < value.length - 1) { event.preventDefault(); onValueChange(value.filter((_, at) => at !== index)); }
        }} />)}
    </svg>
    <p className="mt-2 text-[9px] text-zinc-600">Click to add · Drag or use arrow keys · Delete to remove</p>
  </fieldset>;
}

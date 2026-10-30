"use client";

import { type ReactNode, useRef, useState } from "react";
import { clamp, curvePath, type CurveAxis, type CurvePoint, type CurveValue } from "../../lib/curves/curve";
export type { CurvePoint } from "../../lib/curves/curve";

export type CurveElementProps = {
  label: string; value: readonly CurvePoint[]; onValueChange: (value: CurvePoint[]) => void;
  curve?: CurveValue; onCurveChange?: (curve: CurveValue) => void;
  onValueCommit?: () => void; disabled?: boolean;
  linked?: (index: number, axis: CurveAxis) => boolean;
  renderTerminal?: (index: number, axis: CurveAxis) => ReactNode;
};

function NumberInput({ label, value, min, max, disabled, onCommit }: { label: string; value: number; min: number; max: number; disabled: boolean; onCommit: (value: number) => void }) {
  const [draft, setDraft] = useState<string | null>(null);
  return <label className="flex min-w-0 items-center gap-1 text-[10px] text-zinc-400">{label}
    <input aria-label={label} type="number" step="any" min={min} max={max} disabled={disabled} value={draft ?? Number(value.toFixed(4))}
      onChange={(event) => setDraft(event.target.value)} onBlur={() => {
        if (draft !== null && draft.trim() && Number.isFinite(Number(draft))) onCommit(clamp(Number(draft), min, max));
        setDraft(null);
      }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); } if (event.key === "Escape") { event.stopPropagation(); setDraft(null); } }}
      className="w-full min-w-0 rounded border border-white/10 bg-black/30 px-2 py-1 font-mono text-zinc-100 outline-none focus:border-violet-400 disabled:opacity-40" />
  </label>;
}

export function CurveElement({ label, value, onValueChange, curve, onCurveChange, onValueCommit, disabled = false, linked = () => false, renderTerminal }: CurveElementProps) {
  const [local, setLocal] = useState<CurveValue | null>(null);
  const current: CurveValue = curve ?? (local && local.points.length === value.length ? { ...local, points: [...value] } : { points: [...value], slopes: value.slice(1).map(() => 0), ids: value.map((_, i) => `p${i}`) });
  const { points, slopes, ids } = current;
  const latest = useRef(current); latest.current = current;
  const dragging = useRef<{ kind: "point" | "slope"; index: number; x: number; y: number; slope: number; changed: boolean } | null>(null);
  const [selection, setSelected] = useState<{ kind: "point" | "slope"; id: string }>({ kind: "point", id: ids[0] });
  const selected = ids.includes(selection.id) && (selection.kind === "point" || ids.indexOf(selection.id) < slopes.length) ? selection : { kind: "point" as const, id: ids[0] };
  function change(next: CurveValue) { latest.current = next; if (onCurveChange) onCurveChange(next); else { setLocal(next); onValueChange(next.points); } }
  function update(index: number, x: number, y: number) {
    const base = latest.current;
    const low = index === 0 ? 0 : base.points[index - 1][0] + 0.000001;
    const high = index === base.points.length - 1 ? 1 : base.points[index + 1][0] - 0.000001;
    change({ ...base, points: base.points.map((point, at) => at === index ? [linked(index, "x") ? point[0] : clamp(x, low, high), linked(index, "y") ? point[1] : clamp(y, 0, 1)] : point) });
  }
  function bend(index: number, slope: number) {
    if (linked(index, "slope")) return;
    const base = latest.current;
    change({ ...base, slopes: base.slopes.map((value, at) => at === index ? clamp(slope, -1, 1) : value) });
  }
  function remove(index: number) {
    if (points.length <= 2 || index === 0 || index === points.length - 1 || ["x", "y", "slope"].some((axis) => linked(index, axis as CurveAxis))) return;
    change({ points: points.filter((_, i) => i !== index), ids: ids.filter((_, i) => i !== index), slopes: slopes.filter((_, i) => i !== index) });
    setSelected({ kind: "point", id: ids[index - 1] });
  }
  const selectedIndex = ids.indexOf(selected.id);
  return <fieldset disabled={disabled} className="rounded-lg border border-white/10 bg-black/20 p-2 disabled:opacity-40">
    <legend className="px-1 text-[10px] text-zinc-400">{label}</legend>
    <svg viewBox="0 0 240 120" preserveAspectRatio="none" aria-label={`${label} curve editor`} className="h-32 w-full touch-none select-none overflow-visible rounded bg-violet-400/5 [-webkit-tap-highlight-color:transparent]"
      onPointerDown={(event) => {
        if (disabled || event.button !== 0 || event.detail > 1) return;
        event.preventDefault();
        const rect = event.currentTarget.getBoundingClientRect();
        const x = clamp((event.clientX - rect.left) / rect.width, 0, 1), y = clamp(1 - (event.clientY - rect.top) / rect.height, 0, 1);
        if (x <= points[0][0] || x >= points.at(-1)![0] || points.some((point) => Math.abs(point[0] - x) < 0.01)) return;
        const index = points.findIndex((point) => point[0] > x);
        const next = { points: [...points], ids: [...ids], slopes: [...slopes] };
        next.points.splice(index, 0, [x, y]); next.ids.splice(index, 0, `p${crypto.randomUUID().replaceAll("-", "")}`); next.slopes.splice(index, 0, 0);
        change(next); dragging.current = { kind: "point", index, x: event.clientX, y: event.clientY, slope: 0, changed: true };
        setSelected({ kind: "point", id: next.ids[index] });
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        const drag = dragging.current;
        if (disabled || !drag) return;
        if (!drag.changed && Math.hypot(event.clientX - drag.x, event.clientY - drag.y) < 2) return;
        const rect = event.currentTarget.getBoundingClientRect();
        if (drag.kind === "point") update(drag.index, (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
        else {
          const direction = Math.sign(points[drag.index + 1][1] - points[drag.index][1]) || 1;
          bend(drag.index, drag.slope + (event.clientY - drag.y) / rect.height * 2 * direction);
        }
        drag.changed = true;
      }} onPointerUp={() => { const changed = dragging.current?.changed; dragging.current = null; if (changed) onValueCommit?.(); }}
      onPointerCancel={() => { dragging.current = null; }}>
      {[30, 60, 90].map((y) => <path key={y} d={`M0 ${y}H240`} stroke="#ffffff0c" pointerEvents="none" />)}
      {points.slice(0, -1).map((point, index) => <g key={ids[index]}>
        <path d={curvePath(point, points[index + 1], slopes[index])} fill="none" stroke="#a78bfa" strokeWidth={2} pointerEvents="none" />
        <path d={curvePath(point, points[index + 1], slopes[index])} fill="none" stroke="transparent" strokeWidth={14} className="cursor-ns-resize outline-none focus-visible:stroke-violet-300/20" role="button" aria-label={`Segment ${index + 1} slope`} tabIndex={disabled ? -1 : 0}
          onFocus={() => setSelected({ kind: "slope", id: ids[index] })}
          onPointerDown={(event) => { event.preventDefault(); event.stopPropagation(); if (disabled || event.button !== 0) return; setSelected({ kind: "slope", id: ids[index] }); event.currentTarget.focus({ preventScroll: true }); if (linked(index, "slope")) return; dragging.current = { kind: "slope", index, x: event.clientX, y: event.clientY, slope: slopes[index], changed: false }; event.currentTarget.setPointerCapture(event.pointerId); }}
          onKeyDown={(event) => { if (event.key === "Enter") setSelected({ kind: "slope", id: ids[index] }); if (["ArrowUp", "ArrowDown"].includes(event.key)) { event.preventDefault(); bend(index, slopes[index] + (event.key === "ArrowUp" ? -0.05 : 0.05)); } }} onKeyUp={onValueCommit} />
      </g>)}
      {points.map(([x, y], index) => <circle key={ids[index]} cx={x * 240} cy={(1 - y) * 120} r={4} fill="#ddd6fe" stroke="#7c3aed"
        role="slider" aria-label={`${label} point ${index + 1}`} aria-valuemin={0} aria-valuemax={1} aria-valuenow={y} aria-valuetext={`x ${x.toFixed(3)}, y ${y.toFixed(3)}`} aria-disabled={disabled}
        tabIndex={disabled ? -1 : 0} className="cursor-move outline-none focus:fill-white focus:stroke-white"
        onFocus={() => setSelected({ kind: "point", id: ids[index] })}
        onPointerDown={(event) => { event.preventDefault(); event.stopPropagation(); if (disabled || event.button !== 0) return; setSelected({ kind: "point", id: ids[index] }); event.currentTarget.focus({ preventScroll: true }); dragging.current = { kind: "point", index, x: event.clientX, y: event.clientY, slope: 0, changed: false }; event.currentTarget.setPointerCapture(event.pointerId); }}
        onKeyUp={onValueCommit} onKeyDown={(event) => {
          if (disabled) return;
          if (event.key === "Enter") setSelected({ kind: "point", id: ids[index] });
          if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) { event.preventDefault(); update(index, x + (event.key === "ArrowRight" ? 0.01 : event.key === "ArrowLeft" ? -0.01 : 0), y + (event.key === "ArrowUp" ? 0.01 : event.key === "ArrowDown" ? -0.01 : 0)); }
          if (["Delete", "Backspace"].includes(event.key)) { event.preventDefault(); event.stopPropagation(); remove(index); }
        }} />)}
    </svg>
    {selectedIndex >= 0 && <div className="mt-2 space-y-2 rounded border border-white/10 bg-black/10 p-2">
      <div className="text-[10px] text-violet-200">{selected.kind === "point" ? `Point ${selectedIndex + 1}` : `Segment ${selectedIndex + 1} slope`}</div>
      {selected.kind === "point" ? <div className="grid grid-cols-2 gap-2">{(["x", "y"] as const).map((axis, at) => <NumberInput key={`${selected.id}-${axis}`} label={axis.toUpperCase()} value={points[selectedIndex][at]} min={axis === "x" && selectedIndex ? points[selectedIndex - 1][0] + 0.000001 : 0} max={axis === "x" && selectedIndex < points.length - 1 ? points[selectedIndex + 1][0] - 0.000001 : 1} disabled={disabled || linked(selectedIndex, axis)} onCommit={(value) => { update(selectedIndex, at === 0 ? value : points[selectedIndex][0], at === 1 ? value : points[selectedIndex][1]); onValueCommit?.(); }} />)}</div>
        : <NumberInput key={selected.id} label="Slope" value={slopes[selectedIndex]} min={-1} max={1} disabled={disabled || linked(selectedIndex, "slope")} onCommit={(value) => { bend(selectedIndex, value); onValueCommit?.(); }} />}
    </div>}
    {renderTerminal && <div className="mt-2 space-y-1">{points.map((_, i) => <div key={ids[i]} className="flex items-center gap-3 text-[9px] text-zinc-500">
      <button type="button" className="w-10 text-left hover:text-violet-200" onClick={() => setSelected({ kind: "point", id: ids[i] })}>Point {i + 1}</button>
      {(["x", "y", ...(i < points.length - 1 ? ["slope"] : [])] as CurveAxis[]).map((axis) => <span key={axis} className="flex items-center gap-1">{renderTerminal(i, axis)}<button type="button" onClick={() => setSelected({ kind: axis === "slope" ? "slope" : "point", id: ids[i] })}>{axis}</button></span>)}
    </div>)}</div>}
    <p className="mt-2 text-[9px] text-zinc-600">Click a point or link to edit · Drag to shape · Click background to add · Delete unlinked points</p>
  </fieldset>;
}

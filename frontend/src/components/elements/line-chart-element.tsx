"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type ChartSeries = { id: string; label: string; values: readonly number[]; color: string };
type ChartDisplayProps = { expanded?: boolean; onExpandedChange?: (expanded: boolean) => void; hiddenSeries?: string[]; onHiddenSeriesChange?: (hidden: string[]) => void };
export type MultiLineChartElementProps = ChartDisplayProps & { label: string; series: readonly ChartSeries[]; yMin?: number; yMax?: number };

export function MultiLineChartElement({ label, series, yMin = 0, yMax = 1, expanded = true, onExpandedChange, hiddenSeries, onHiddenSeriesChange }: MultiLineChartElementProps) {
  const [localHidden, setLocalHidden] = useState<string[]>([]);
  const hidden = hiddenSeries ?? localHidden;
  const setHidden = onHiddenSeriesChange ?? setLocalHidden;
  const count = Math.max(0, ...series.map((line) => line.values.length));
  const rows = Array.from({ length: count }, (_, index) => Object.fromEntries([
    ["index", index], ...series.map((line) => [line.id, line.values[index] ?? null]),
  ]));
  return <details open={expanded} onToggle={(event) => { if (event.currentTarget.open !== expanded) onExpandedChange?.(event.currentTarget.open); }} className="rounded-lg border border-white/10 bg-black/20">
    <summary className="cursor-pointer px-3 py-2 text-[10px] text-zinc-400 outline-violet-400">{label}</summary>
    <div role="img" aria-label={`${label}, ${series.length} series, ${count} samples`} className="h-36 px-1">
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 250, height: 144 }}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#ffffff0d" />
          <XAxis dataKey="index" hide />
          <YAxis domain={[yMin, yMax]} allowDataOverflow tickCount={3} width={24} tick={{ fill: "#71717a", fontSize: 9 }} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ background: "#23232e", border: "1px solid #ffffff18", borderRadius: 6, fontSize: 10 }} />
          {series.map((line) => <Line key={line.id} dataKey={(row) => row[line.id]} name={line.label} stroke={line.color} strokeWidth={1.5} dot={count === 1} hide={hidden.includes(line.id)} isAnimationActive={false} />)}
        </LineChart>
      </ResponsiveContainer>
    </div>
    {!count && <p className="pb-2 text-center text-[10px] text-zinc-600">No samples</p>}
    <div className="flex flex-wrap gap-2 px-3 pb-2">{series.map((line) => <button key={line.id} type="button" aria-label={`Show ${line.label}`} aria-pressed={!hidden.includes(line.id)}
      onClick={() => setHidden(hidden.includes(line.id) ? hidden.filter((id) => id !== line.id) : [...hidden, line.id])}
      className={`flex items-center gap-1 rounded px-1 py-0.5 text-[9px] text-zinc-400 outline-violet-400 ${hidden.includes(line.id) ? "opacity-35" : ""}`}>
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: line.color }} />{line.label}
    </button>)}</div>
  </details>;
}

export function LineChartElement({ label, data, color = "#a78bfa", yMin = 0, yMax = 1, ...display }: ChartDisplayProps & { label: string; data: readonly number[]; color?: string; yMin?: number; yMax?: number }) {
  return <MultiLineChartElement {...display} label={label} series={[{ id: "value", label, values: data, color }]} yMin={yMin} yMax={yMax} />;
}

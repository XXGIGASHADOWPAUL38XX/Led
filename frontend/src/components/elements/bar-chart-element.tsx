"use client";

import { useId } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type BarChartElementProps = {
  data: readonly number[];
  colors?: readonly string[];
  yMin?: number;
  yMax?: number;
  xMin?: number;
  xMax?: number;
  preview?: boolean;
  label?: string;
  xUnit?: string;
  xScale?: "linear" | "logarithmic";
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
};

export function BarChartElement({ data, colors, yMin = 0, yMax = 60, xMin = 20, xMax = 5000, preview = false, label = "Spectrum", xUnit = "Hz", xScale = "logarithmic", expanded = true, onExpandedChange }: BarChartElementProps) {
  const gradient = useId();
  const points = data.map((value, index) => ({
    value,
    frequency: Math.round(xScale === "logarithmic" ? xMin * (xMax / xMin) ** (index / Math.max(1, data.length - 1)) : xMin + (xMax - xMin) * index / Math.max(1, data.length - 1)),
  }));

  return (
    <details open={expanded} onToggle={(event) => { if (event.currentTarget.open !== expanded) onExpandedChange?.(event.currentTarget.open); }} className="group/chart overflow-hidden rounded-lg border border-white/10 bg-black/20">
      <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-[10px] text-zinc-400 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-400 [&::-webkit-details-marker]:hidden">
        <span>{preview ? `${label} preview` : label}</span>
        <span aria-hidden="true" className="text-zinc-500 transition-transform group-open/chart:rotate-180">▾</span>
      </summary>
      <div role="img" aria-label={`${label}, ${data.length} bars, range ${yMin} to ${yMax}`} className="h-36 px-1">
        <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 250, height: 144 }}>
          <BarChart data={points} barCategoryGap={0} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#c4b5fd" /><stop offset="100%" stopColor="#7c3aed" stopOpacity={0.45} /></linearGradient></defs>
            <CartesianGrid vertical={false} stroke="#ffffff0d" />
            <YAxis domain={[yMin, yMax]} allowDataOverflow tickCount={3} width={24} tick={{ fill: "#71717a", fontSize: 9 }} tickLine={false} axisLine={false} />
            <XAxis dataKey="frequency" hide />
            <Tooltip cursor={{ fill: "#ffffff08" }} labelFormatter={(label) => `${label} ${xUnit}`.trim()} formatter={(value) => [Number(value).toFixed(2), "Value"]}
              contentStyle={{ background: "#23232e", border: "1px solid #ffffff18", borderRadius: 6, fontSize: 10 }} labelStyle={{ color: "#a1a1aa" }} itemStyle={{ color: "#c4b5fd" }} />
            <Bar dataKey="value" fill={`url(#${gradient})`} isAnimationActive={false}>
              {colors?.map((fill, index) => <Cell key={index} fill={fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-between px-3 pt-1 pb-2 font-mono text-[9px] text-zinc-500"><span>{xMin.toLocaleString("en")} {xUnit}</span><span>{xMax.toLocaleString("en")} {xUnit}</span></div>
    </details>
  );
}

"use client";

import { useState } from "react";
import { DataElement } from "./data-element";
import { BarChartElement } from "./bar-chart-element";
import { LineChartElement } from "./line-chart-element";
import { SelectElement } from "./select-element";
import { IntervalElement } from "./interval-element";

export function AnalysableElement({ label, data, yMin = 0, yMax = 1 }: { label: string; data: readonly number[]; yMin?: number; yMax?: number }) {
  const [kind, setKind] = useState(data.length === 1 ? "line" : "bars");
  const [range, setRange] = useState<[number, number]>([yMin, yMax]);
  return <div className="space-y-1.5">
    <DataElement label={label} direction="output" shape={[data.length]} />
    <SelectElement label="View" value={kind} onValueChange={setKind} options={[{ value: "bars", label: "Bars" }, { value: "line", label: "Line" }]} />
    <IntervalElement label="Y range" value={range} onValueChange={([low, high]) => { if (low < high) setRange([low, high]); }} min={yMin} max={yMax} step={(yMax - yMin) / 100} />
    {kind === "bars" ? <BarChartElement label="Values" xMin={0} xMax={Math.max(0, data.length - 1)} xScale="linear" xUnit="" data={data} yMin={range[0]} yMax={range[1]} /> : <LineChartElement label="History" data={data} yMin={range[0]} yMax={range[1]} />}
  </div>;
}

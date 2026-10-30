"use client";

import { useState } from "react";
import { Node } from "../node/node";
import { MultiLineChartElement, LineChartElement } from "../elements/line-chart-element";
import { AnalysableElement } from "../elements/analysable-element";
import { TriggerElement } from "../elements/trigger-element";
import { SwitchElement } from "../elements/switch-element";
import { ChartLineReferenceElement } from "../elements/chart-line-reference-element";
import type { Color } from "../elements/color-element";
import type { ElementReference, ReferenceNode } from "../elements/reference-element";

const history = Array.from({ length: 60 }, (_, index) => 0.5 + Math.sin(index / 6) * 0.35);
const side = history.map((value, index) => value * (0.6 + Math.cos(index / 4) * 0.2));
const nodes: ReferenceNode[] = [
  { id: "amplitudes-1", label: "Amplitudes", elements: [{ id: "data", label: "Data" }, { id: "frequencies", label: "Frequencies" }] },
  { id: "buffer-1", label: "Buffer", elements: [{ id: "data", label: "Data" }] },
];

export function AnalysisPreview() {
  const [active, setActive] = useState(false);
  const [reference, setReference] = useState<ElementReference | null>(null);
  const [color, setColor] = useState<Color>([167, 139, 250]);
  const [visible, setVisible] = useState(true);
  const stroke = `rgb(${color.slice(0, 3).join(",")})`;
  return <Node id="analysis-1" title="Analysis" description="UI preview · sample histories, no live signal connected.">
    <SwitchElement label="Preview trigger" checked={active} onCheckedChange={setActive} />
    <TriggerElement label="Trigger" active={active} />
    <LineChartElement label="Level preview" data={history} />
    <MultiLineChartElement label="Stereo preview" series={[
      { id: "mid", label: "Mid", values: history, color: "#a78bfa" },
      { id: "side", label: "Side", values: side, color: "#38bdf8" },
    ]} />
    <ChartLineReferenceElement label="Chart source" nodes={nodes} value={reference} onValueChange={setReference}
      color={color} onColorChange={setColor} visible={visible} onVisibleChange={setVisible} />
    <MultiLineChartElement label="Configured line preview" series={visible ? [{ id: "configured", label: "Selected stroke", values: history, color: stroke }] : []} />
    <AnalysableElement label="Signal preview" data={side} />
  </Node>;
}

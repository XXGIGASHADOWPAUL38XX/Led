"use client";

import { useEffect, useState } from "react";
import { backend } from "@/lib/backend/store";
import { useGraph } from "@/lib/backend/hooks";
import { CurveElement } from "../elements/curve-element";
import { Terminal } from "../workspace/terminal";
import { clamp, curvePort, type CurveAxis, type CurveValue } from "../../lib/curves/curve";

/** Only linked controls are streamed; authored values remain editable fallbacks. */
export function FunctionCurveControl({ nodeId, label, curve, onChange, onCommit, disabled }: {
  nodeId: string; label: string; curve: CurveValue; onChange: (curve: CurveValue) => void; onCommit?: () => void; disabled: boolean;
}) {
  const snapshot = useGraph();
  const connections = snapshot?.graph.connections.filter((edge) => edge.target.nodeId === nodeId && edge.target.element.startsWith("point_")) ?? [];
  const ports = connections.map((edge) => edge.target.element).sort();
  const signature = JSON.stringify(ports);
  const [, refresh] = useState(0);
  useEffect(() => {
    const names: string[] = JSON.parse(signature);
    const unsubscribe = names.map((name) => backend.watchArray(nodeId, name, () => refresh((value) => value + 1)));
    return () => unsubscribe.forEach((stop) => stop());
  }, [nodeId, signature]);
  const linked = (index: number, axis: CurveAxis) => ports.includes(curvePort(curve.ids[index], axis));
  const read = (index: number, axis: CurveAxis, fallback: number) => {
    const value = backend.array(nodeId, curvePort(curve.ids[index], axis));
    return linked(index, axis) && value ? Number(value.data[0]) : fallback;
  };
  const points: CurveValue["points"] = [];
  curve.points.forEach(([x, y], i) => points.push([
    clamp(read(i, "x", x), i ? points[i - 1][0] + 0.000001 : 0, 1 - (curve.points.length - 1 - i) * 0.000001),
    clamp(read(i, "y", y), 0, 1),
  ]));
  const live = { ...curve, points, slopes: curve.slopes.map((value, i) => clamp(read(i, "slope", value), -1, 1)) };
  return <CurveElement label={label} value={live.points} curve={live} disabled={disabled} linked={linked} onValueChange={() => {}} onValueCommit={onCommit}
    onCurveChange={(next) => onChange({ ...next,
      points: next.points.map((point, i) => {
        const previous = curve.ids.indexOf(next.ids[i]);
        return previous < 0 ? point : [linked(previous, "x") ? curve.points[previous][0] : point[0], linked(previous, "y") ? curve.points[previous][1] : point[1]];
      }),
      slopes: next.slopes.map((value, i) => { const previous = curve.ids.indexOf(next.ids[i]); return previous >= 0 && linked(previous, "slope") ? curve.slopes[previous] : value; }),
    })}
    renderTerminal={nodeId ? (i, axis) => <Terminal endpoint={{ nodeId, element: curvePort(curve.ids[i], axis) }} direction="input" /> : undefined} />;
}

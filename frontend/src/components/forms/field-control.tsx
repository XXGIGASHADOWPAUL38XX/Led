"use client";

import { useState } from "react";
import { useGraph } from "@/lib/backend/hooks";
import { isArrayValue, type ArrayValue, type ElementDescriptor, type NodeDescriptor } from "@/lib/backend/protocol";
import type { FieldDefinition } from "../node/definition";
import { ArrayElement, AxisElement, ColorElement, CurveElement, DataElement, IntervalElement, OptionalSliderElement, OperatorElement,
  ReferenceElement, SelectElement, SequenceElement, SliderElement, SwitchElement, TextElement, type Color, type CurvePoint, type NumericArray } from "../elements";

type Reference = { nodeId: string; element?: string } | null;
export function plainArray(array: ArrayValue): NumericArray {
  const values = Array.from(array.data, Number);
  function nest(shape: number[], start: number): NumericArray {
    if (shape.length <= 1) return values.slice(start, start + (shape[0] ?? 1));
    const stride = shape.slice(1).reduce((product, size) => product * size, 1);
    return Array.from({ length: shape[0] }, (_, index) => nest(shape.slice(1), start + index * stride));
  }
  return nest(array.shape, 0);
}

export function ReferenceControl({ nodeId, field, value, onChange, disabled = false, nodeOnly = false }: {
  nodeId: string; field: FieldDefinition; value: Reference; onChange: (value: Reference) => void; disabled?: boolean; nodeOnly?: boolean;
}) {
  const snapshot = useGraph();
  const [draft, setDraft] = useState<{ nodeId: string; elementId: string | null } | null>(null);
  const expectedShape = snapshot?.nodes.find((node) => node.id === nodeId)?.elements.find((element) => element.name === field.matchInput)?.shape;
  const nodes = (snapshot?.nodes ?? []).filter((node) => node.id !== nodeId && (!field.nodeTypes || field.nodeTypes.includes(node.type))
    && (!expectedShape || node.ports.some((port) => port.direction === "out" && JSON.stringify(port.shape) === JSON.stringify(expectedShape))));
  const label = field.label ?? field.name.replaceAll("_", " ");
  if (nodeOnly) return <SelectElement label={label} disabled={disabled} value={value?.nodeId ?? "automatic"}
    options={[{ value: "automatic", label: "Automatic" }, ...nodes.map((node) => ({ value: node.id, label: node.id }))]}
    onValueChange={(id) => onChange(id === "automatic" ? null : { nodeId: id })} />;
  return <ReferenceElement label={label} disabled={disabled} value={draft ?? (value ? { nodeId: value.nodeId, elementId: value.element ?? null } : null)}
    nodes={nodes.map((node) => ({ id: node.id, label: node.id, elements: node.ports.filter((port) => port.direction === "out").map((port) => ({ id: port.name, label: port.name })) }))}
    onValueChange={(reference) => {
      if (reference && !reference.elementId) { setDraft(reference); return; }
      setDraft(null);
      onChange(reference ? { nodeId: reference.nodeId, element: reference.elementId! } : null);
    }} />;
}

function TokenControl({ nodeId, field, value, onChange, onCommit }: { nodeId: string; field: FieldDefinition; value: unknown; onChange: (value: unknown) => void; onCommit?: () => void }) {
  const commit = (value: unknown) => { onChange(value); onCommit?.(); };
  const operator = typeof value === "string" && ["+", "-", "*", "/", "**", "<", "<=", "==", ">=", ">", "&", "|", "(", ")"].includes(value);
  const kind = typeof value === "object" && value !== null ? "source" : typeof value === "number" ? "number" : operator ? "operator" : "text";
  return <div className="space-y-2">
    <SelectElement label="Value type" value={kind} options={["source", "number", "operator", "text"].map((value) => ({ value, label: value }))}
      onValueChange={(next) => commit(next === "source" ? {} : next === "number" ? 1 : next === "operator" ? "*" : "")} />
    {kind === "source" ? <ReferenceControl nodeId={nodeId} field={field} value={value as Reference} onChange={commit} />
      : kind === "operator" ? <OperatorElement label="Operator" value={String(value)} onValueChange={commit} />
      : kind === "number" ? <SliderElement label="Number" value={Number(value)} onValueChange={onChange} onValueCommit={onCommit} min={-10000} max={10000} step={0.01} />
      : <TextElement label="Token" value={String(value)} onValueChange={onChange} onValueCommit={onCommit} />}
  </div>;
}

export function FieldControl({ node, field, element, value, onChange, onCommit, disabled = false }: { node: NodeDescriptor; field: FieldDefinition; element: ElementDescriptor; value: unknown; onChange: (value: unknown) => void; onCommit?: () => void; disabled?: boolean }) {
  const commit = (value: unknown) => { onChange(value); onCommit?.(); };
  const label = field.label ?? element.label;
  const common = { label, disabled: element.disabled || disabled };
  if (field.control === "port" || element.disabled && isArrayValue(value)) return <DataElement label={label} direction="input" endpoint={{ nodeId: node.id, element: field.name }} shape={element.shape ?? (isArrayValue(value) ? value.shape : [])} unit={field.unit} />;
  switch (field.control) {
    case "slider": {
      const props = { ...common, min: element.min ?? 0, max: element.max ?? 1, step: element.integer ? 1 : 0.01, onValueCommit: onCommit, scale: (element.min ?? 0) > 0 ? field.scale : "linear" as const, unit: field.unit };
      return element.optional ? <OptionalSliderElement {...props} value={value === null ? null : Number(value)} onValueChange={onChange} /> : <SliderElement {...props} value={Number(value)} onValueChange={onChange} />;
    }
    case "switch": return <SwitchElement {...common} checked={Boolean(value)} onCheckedChange={commit} />;
    case "select": return <SelectElement {...common} value={String(value)} onValueChange={commit} options={(element.options ?? []).map((option) => ({ ...option, value: String(option.value) }))} />;
    case "axis": return <AxisElement {...common} value={value as number | number[] | null} onValueChange={commit} />;
    case "color": return <ColorElement {...common} value={value as Color} onValueChange={onChange} onValueCommit={onCommit} />;
    case "interval": return <IntervalElement {...common} value={value as [number, number]} onValueChange={onChange} onValueCommit={onCommit} min={field.min ?? -10000} max={field.max ?? 10000} />;
    case "array": return <ArrayElement {...common} value={isArrayValue(value) ? plainArray(value) : value as NumericArray} onValueChange={commit} min={element.min} max={element.max} integer={element.dtype ? /[iu]/.test(element.dtype) : false} />;
    case "curve": return <CurveElement {...common} value={(isArrayValue(value) ? plainArray(value) : value) as CurvePoint[]} onValueChange={onChange} onValueCommit={onCommit} />;
    case "reference": return <ReferenceControl nodeId={node.id} field={field} value={value as Reference} onChange={commit} disabled={common.disabled} />;
    case "node-reference": return <ReferenceControl nodeId={node.id} field={field} value={value as Reference} onChange={commit} disabled={common.disabled} nodeOnly />;
    case "sequence": return <SequenceElement {...common} value={value as unknown[]} onValueChange={onChange} onValueCommit={onCommit}
      createItem={() => field.item === "token" ? "*" : null}
      renderItem={(item, _index, set) => field.item === "token" ? <TokenControl nodeId={node.id} field={field} value={item} onChange={set} onCommit={onCommit} />
        : <ReferenceControl nodeId={node.id} field={field} value={item as Reference} onChange={(value) => { set(value); onCommit?.(); }} nodeOnly={field.item === "node"} />} />;
    case "managed": return <p className="px-1 text-[10px] text-zinc-500">{label} · managed by Python</p>;
    default: return <TextElement {...common} value={String(value ?? "")} onValueChange={onChange} onValueCommit={onCommit} kind={field.name.includes("url") ? "url" : field.name.includes("path") ? "path" : "name"} />;
  }
}

"use client";

import { useState } from "react";
import { Node } from "../node/node";
import { TextElement } from "../elements/text-element";
import { ColorElement, type Color } from "../elements/color-element";
import { IntervalElement } from "../elements/interval-element";
import { ReferenceElement, type ElementReference, type ReferenceNode } from "../elements/reference-element";

const nodes: ReferenceNode[] = [
  { id: "buffer-1", label: "Buffer", elements: [{ id: "data", label: "Data" }] },
  { id: "amplitudes-1", label: "Amplitudes", elements: [{ id: "frequencies", label: "Frequencies" }, { id: "data", label: "Data" }] },
];

export function ControlsPreview() {
  const [name, setName] = useState("Ambient wash");
  const [url, setUrl] = useState("");
  const [path, setPath] = useState("");
  const [rgb, setRgb] = useState<Color>([139, 92, 246]);
  const [rgba, setRgba] = useState<Color>([56, 189, 248, 180]);
  const [interval, setInterval] = useState<[number, number]>([0.2, 0.8]);
  const [reference, setReference] = useState<ElementReference | null>(null);
  return (
    <Node id="controls-1" title="Controls" description="UI preview · values and references ready for backend updates.">
      <TextElement label="Name" value={name} onValueChange={setName} placeholder="Node name" />
      <TextElement label="URL" kind="url" value={url} onValueChange={setUrl} placeholder="https://…" />
      <TextElement label="Path" kind="path" value={path} onValueChange={setPath} placeholder="/music/…" />
      <ColorElement label="Color" value={rgb} onValueChange={setRgb} />
      <ColorElement label="Glow" value={rgba} onValueChange={setRgba} />
      <IntervalElement label="Range" value={interval} onValueChange={setInterval} min={0} max={1} step={0.01} />
      <ReferenceElement label="Source reference" nodes={nodes} value={reference} onValueChange={setReference} />
    </Node>
  );
}

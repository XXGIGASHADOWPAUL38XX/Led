"use client";

import { useState } from "react";
import { Node } from "../node/node";
import { ArrayElement, type NumericArray } from "../elements/array-element";
import { SequenceElement } from "../elements/sequence-element";
import { CurveElement, type CurvePoint } from "../elements/curve-element";
import { TextElement } from "../elements/text-element";
import { OptionalSliderElement } from "../elements/optional-slider-element";
import { AxisElement, EnumElement, OperatorElement } from "../elements/typed-select-element";

export function EditorsPreview() {
  const [array, setArray] = useState<NumericArray>([[0, 0.5], [1, 0.8]]);
  const [sequence, setSequence] = useState(["Attack", "Fade"]);
  const [curve, setCurve] = useState<CurvePoint[]>([[0, 0], [0.4, 0.8], [1, 1]]);
  return <Node id="editors-1" title="Editors" description="UI preview · authored arrays, ordered items, and curves.">
    <ArrayElement label="Points" value={array} onValueChange={setArray} min={0} max={1} />
    <SequenceElement label="Steps" value={sequence} onValueChange={setSequence} createItem={() => "New step"}
      renderItem={(item, index, onValueChange) => <TextElement label={`Step ${index + 1}`} value={item} onValueChange={onValueChange} />} />
    <CurveElement label="Envelope" value={curve} onValueChange={setCurve} />
  </Node>;
}

export function ParametersPreview() {
  const [gain, setGain] = useState<number | null>(null);
  const [axis, setAxis] = useState<number | number[] | null>(0);
  const [mode, setMode] = useState("linear");
  const [operation, setOperation] = useState("*");
  return <Node id="parameters-1" title="Parameters" description="UI preview · optional values and typed choices.">
    <OptionalSliderElement label="Gain override" value={gain} onValueChange={setGain} min={0} max={2} step={0.01} defaultValue={1} />
    <AxisElement label="Axis" value={axis} onValueChange={setAxis} />
    <EnumElement label="Gradient" value={mode} onValueChange={setMode} options={[{ value: "linear", label: "Linear" }, { value: "mirror", label: "Mirror" }]} />
    <OperatorElement label="Operation" value={operation} onValueChange={setOperation} />
  </Node>;
}

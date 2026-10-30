"use client";

import { ReferenceElement, type ReferenceElementProps } from "./reference-element";
import { ColorElement, type Color } from "./color-element";
import { SwitchElement } from "./switch-element";

export type ChartLineReferenceElementProps = ReferenceElementProps & {
  color: Color;
  onColorChange: (color: Color) => void;
  visible: boolean;
  onVisibleChange: (visible: boolean) => void;
};

export function ChartLineReferenceElement({ color, onColorChange, visible, onVisibleChange, ...props }: ChartLineReferenceElementProps) {
  return <div className="space-y-1.5">
    <ReferenceElement {...props} />
    <ColorElement label="Stroke" value={color} onValueChange={onColorChange} disabled={props.disabled} />
    <SwitchElement label="Visible" checked={visible} onCheckedChange={onVisibleChange} disabled={props.disabled} />
  </div>;
}

"use client";

import { SliderElement, type SliderElementProps } from "./slider-element";
import { SwitchElement } from "./switch-element";

export type OptionalSliderElementProps = Omit<SliderElementProps, "value" | "onValueChange"> & {
  value: number | null;
  onValueChange: (value: number | null) => void;
  defaultValue?: number;
};

export function OptionalSliderElement({ label, value, onValueChange, onValueCommit, defaultValue, ...props }: OptionalSliderElementProps) {
  return <div className="space-y-1.5">
    <SwitchElement label={label} checked={value !== null} disabled={props.disabled} onCheckedChange={(enabled) => { onValueChange(enabled ? defaultValue ?? props.min : null); onValueCommit?.(); }} />
    {value !== null && <SliderElement {...props} label="Value" value={value} onValueChange={onValueChange} onValueCommit={onValueCommit} />}
  </div>;
}

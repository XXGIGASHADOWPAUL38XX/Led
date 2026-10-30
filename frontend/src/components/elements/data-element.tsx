"use client";

import { useId } from "react";
import { CoreElement } from "./core-element";
import type { Endpoint } from "@/lib/backend/protocol";

export type DataElementProps = {
  label: string;
  direction: "input" | "output";
  shape: readonly number[];
  unit?: string;
  endpoint?: Endpoint;
};

export function DataElement({ label, direction, shape, unit, endpoint }: DataElementProps) {
  const id = useId();
  return (
    <CoreElement id={id} label={label} port={direction} endpoint={endpoint}>
      <span aria-labelledby={`${id}-label`} className="absolute inset-y-0 right-3 flex items-center gap-2 font-mono text-[10px] text-zinc-500">
        <span>{shape.join(" × ")}</span>
        {unit && <span>{unit}</span>}
      </span>
    </CoreElement>
  );
}

"use client";

import { useId } from "react";
import { CoreElement } from "./core-element";

export function TriggerElement({ label, active }: { label: string; active: boolean }) {
  const id = useId();
  return <CoreElement id={id} label={label} port="output">
    <span role="status" aria-labelledby={`${id}-label`} className="absolute inset-y-0 right-3 flex items-center gap-2 text-[10px] text-zinc-500">
      {active ? "Active" : "Idle"}
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full transition-colors ${active ? "bg-emerald-300 shadow-[0_0_10px_#6ee7b780]" : "bg-zinc-700"}`} />
    </span>
  </CoreElement>;
}

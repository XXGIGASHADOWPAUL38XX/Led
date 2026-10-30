"use client";

import * as Switch from "@radix-ui/react-switch";
import { useId } from "react";
import { CoreElement } from "./core-element";

export type SwitchElementProps = {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
};

export function SwitchElement({ label, checked, onCheckedChange, disabled = false }: SwitchElementProps) {
  const id = useId();

  return (
    <CoreElement id={id} label={label} disabled={disabled}>
      <Switch.Root id={id} checked={checked} onCheckedChange={onCheckedChange} disabled={disabled}
        aria-labelledby={`${id}-label`}
        className="group/switch absolute inset-0 flex items-center justify-end rounded-[inherit] px-3 outline-none transition-colors data-[state=checked]:bg-violet-400/10">
        <span aria-hidden="true" className="relative h-4 w-8 rounded-full bg-white/10 ring-1 ring-white/10 transition-colors group-data-[state=checked]/switch:bg-violet-500/70 group-data-[state=checked]/switch:ring-violet-300/30">
          <Switch.Thumb className="absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-zinc-400 shadow-sm transition-[transform,background-color] data-[state=checked]:translate-x-4 data-[state=checked]:bg-violet-100 motion-reduce:transition-none" />
        </span>
      </Switch.Root>
    </CoreElement>
  );
}

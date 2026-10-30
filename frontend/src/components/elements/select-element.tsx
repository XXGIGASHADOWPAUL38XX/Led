"use client";

import * as Select from "@radix-ui/react-select";
import { useId, useState } from "react";
import { CoreElement } from "./core-element";

export type SelectElementProps = {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  options: readonly { value: string; label: string; disabled?: boolean }[];
  placeholder?: string;
  disabled?: boolean;
};

export function SelectElement({ label, value, onValueChange, options, placeholder = "Select…", disabled = false }: SelectElementProps) {
  const id = useId();
  const [trigger, setTrigger] = useState<HTMLButtonElement | null>(null);

  return (
    <CoreElement id={id} label={label} disabled={disabled}>
      <Select.Root value={value} onValueChange={onValueChange} disabled={disabled}>
        <Select.Trigger ref={setTrigger} id={id} aria-labelledby={`${id}-label`}
          className="absolute inset-0 flex items-center justify-end gap-2 rounded-[inherit] pr-3 pl-24 text-xs text-zinc-100 outline-none transition-colors hover:bg-white/5 data-[state=open]:bg-violet-400/10">
          <span className="truncate"><Select.Value placeholder={placeholder}>{options.find((option) => option.value === value)?.label}</Select.Value></span>
          <Select.Icon className="shrink-0 text-zinc-500">▾</Select.Icon>
        </Select.Trigger>
        <Select.Portal container={trigger?.closest("dialog") ?? undefined}>
          <Select.Content position="popper" sideOffset={6} collisionPadding={12}
            className="z-50 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-lg border border-white/10 bg-[#23232e] p-1 shadow-xl shadow-black/40">
            <Select.ScrollUpButton className="flex h-5 items-center justify-center text-violet-300">▴</Select.ScrollUpButton>
            <Select.Viewport className="max-h-60">
              {options.map((option) => (
                <Select.Item key={option.value} value={option.value} disabled={option.disabled}
                  className="relative cursor-pointer select-none rounded px-3 py-2 pr-8 text-xs text-zinc-300 outline-none data-[highlighted]:bg-violet-400/15 data-[highlighted]:text-white data-[state=checked]:text-violet-200 data-[disabled]:pointer-events-none data-[disabled]:opacity-35">
                  <Select.ItemText>{option.label}</Select.ItemText>
                  <Select.ItemIndicator className="absolute inset-y-0 right-3 flex items-center text-violet-300">✓</Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
            <Select.ScrollDownButton className="flex h-5 items-center justify-center text-violet-300">▾</Select.ScrollDownButton>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </CoreElement>
  );
}

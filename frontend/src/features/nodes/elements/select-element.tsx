import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

export function SelectElement({
  label,
  value,
  onValueChange,
  options,
  placeholder = "Select…",
  disabled = false,
}: SelectElementProps) {
  const id = useId();
  // Radix renders every item even while closed; the trigger already shows the label, so items mount on open only.
  const [open, setOpen] = useState(false);

  return (
    <CoreElement id={id} label={label} disabled={disabled}>
      <Select value={value} onValueChange={onValueChange} disabled={disabled} open={open} onOpenChange={setOpen}>
        <SelectTrigger
          id={id}
          aria-labelledby={`${id}-label`}
          className="absolute inset-0 rounded-[inherit] pr-3 pl-24"
        >
          <SelectValue placeholder={placeholder}>{options.find((option) => option.value === value)?.label}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {open &&
            options.map((option) => (
              <SelectItem key={option.value} value={option.value} disabled={option.disabled}>
                {option.label}
              </SelectItem>
            ))}
        </SelectContent>
      </Select>
    </CoreElement>
  );
}

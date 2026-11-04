import { useId } from "react";
import { Switch } from "@/components/ui/switch";
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
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        aria-labelledby={`${id}-label`}
        className="absolute inset-0 rounded-[inherit] px-3"
      />
    </CoreElement>
  );
}

"use client";

import { useId } from "react";
import { CoreElement } from "./core-element";

export type TextElementProps = {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  onValueCommit?: () => void;
  kind?: "name" | "url" | "path";
  placeholder?: string;
  disabled?: boolean;
  error?: string;
};

export function TextElement({ label, value, onValueChange, onValueCommit, kind = "name", placeholder, disabled = false, error }: TextElementProps) {
  const id = useId();
  return (
    <CoreElement id={id} label={label} disabled={disabled} error={error}>
      <input id={id} type={kind === "url" ? "url" : "text"} aria-labelledby={`${id}-label`}
        aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined}
        value={value} onChange={(event) => onValueChange(event.target.value)} placeholder={placeholder}
        onBlur={onValueCommit} onKeyDown={(event) => { if (event.key === "Enter" && onValueCommit) { event.preventDefault(); onValueCommit(); } }}
        disabled={disabled} spellCheck={false} autoCapitalize="none" autoComplete="off" title={value}
        className="absolute inset-0 w-full rounded-[inherit] pr-3 pl-24 text-right text-xs text-zinc-200 outline-none placeholder:text-zinc-600" />
    </CoreElement>
  );
}

import type { ReactNode } from "react";
import type { Endpoint } from "@/lib/backend/protocol";
import { Terminal } from "../workspace/terminal";

export type CoreElementProps = {
  id: string;
  label: string;
  port?: "input" | "output";
  endpoint?: Endpoint;
  disabled?: boolean;
  error?: string;
  children: ReactNode;
};

export function CoreElement({ id, label, disabled = false, error, children, port, endpoint }: CoreElementProps) {
  return (
    <div className="space-y-1">
      <div data-disabled={disabled || undefined} data-error={Boolean(error) || undefined}
        className="group relative h-9 rounded-md border border-white/10 bg-black/20 transition-colors hover:border-white/20 focus-within:border-violet-400/70 focus-within:ring-2 focus-within:ring-violet-400/15 data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[error]:border-rose-400">
        {port && <Terminal endpoint={endpoint} direction={port} className={`absolute top-1/2 -translate-y-1/2 ${port === "input" ? "-left-5" : "-right-5"}`} />}
        <span id={`${id}-label`} className="pointer-events-none absolute inset-y-0 left-3 z-10 flex items-center text-xs font-medium text-zinc-200">{label}</span>
        {children}
      </div>
      {error && <p id={`${id}-error`} role="alert" className="text-xs text-rose-300">{error}</p>}
    </div>
  );
}

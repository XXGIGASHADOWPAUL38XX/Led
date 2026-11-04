import type { ReactNode } from "react";
import { Terminal } from "../graph/terminal";

export type NodeProps = {
  children?: ReactNode;
  id: string;
  title: string;
  description?: string;
  inputs?: string[];
  outputs?: string[];
  selected?: boolean;
};

/** Node card rendered inside a React Flow node; React Flow owns position, drag and focus. */
export function Node({ id, title, description, inputs = [], outputs = [], children, selected = false }: NodeProps) {
  return (
    <article
      aria-label={`${title} node`}
      data-node-id={id}
      data-selected={selected || undefined}
      onContextMenu={(event) => {
        if (event.ctrlKey) event.preventDefault();
      }}
      className="w-72 rounded-xl border border-violet-400/50 bg-card shadow-2xl shadow-black/40 data-[selected]:border-violet-200 data-[selected]:ring-2 data-[selected]:ring-violet-400/70"
    >
      <header className="node-drag-handle flex w-full cursor-grab touch-none items-center gap-3 rounded-t-xl border-b border-border px-4 py-3 text-left select-none active:cursor-grabbing">
        <span className="h-2 w-2 rounded-full bg-violet-400" />
        <span className="flex-1 text-sm font-semibold">{title}</span>
        <span aria-hidden="true" className="text-muted-foreground">
          ⠿
        </span>
      </header>
      {description && <p className="px-4 py-4 text-xs leading-5 text-zinc-400">{description}</p>}
      {children && <div className="space-y-2 px-3 pb-4">{children}</div>}
      <div className="flex justify-between gap-4 pb-4 text-xs text-zinc-300">
        <div className="space-y-3">
          {inputs.map((name) => (
            <div key={name} className="flex items-center gap-2">
              <Terminal endpoint={{ nodeId: id, element: name }} direction="input" className="-ml-1.5" />
              {name}
            </div>
          ))}
        </div>
        <div className="space-y-3">
          {outputs.map((name) => (
            <div key={name} className="flex items-center justify-end gap-2">
              {name}
              <Terminal endpoint={{ nodeId: id, element: name }} direction="output" className="-mr-1.5" />
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}

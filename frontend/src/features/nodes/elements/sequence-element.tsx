import { IconButton } from "@/components/ui/icon-button";
import { ArrowDown, ArrowUp, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReactNode } from "react";
import type { Endpoint } from "@/api/protocol";
import { Terminal } from "../../graph/terminal";
import { terminalKey } from "../../graph/terminal-compatibility";

export type SequenceElementProps<T> = {
  label: string;
  value: readonly T[];
  onValueChange: (value: T[]) => void;
  onValueCommit?: () => void;
  createItem: () => T;
  renderItem: (item: T, index: number, onChange: (value: T) => void) => ReactNode;
  disabled?: boolean;
  addEndpoint?: Endpoint;
};

export function SequenceElement<T>({
  label,
  value,
  onValueChange,
  onValueCommit,
  createItem,
  renderItem,
  disabled = false,
  addEndpoint,
}: SequenceElementProps<T>) {
  function move(index: number, offset: number) {
    const next = [...value];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    onValueChange(next);
    onValueCommit?.();
  }
  return (
    <fieldset
      disabled={disabled}
      className="space-y-2 rounded-lg border border-border bg-black/10 p-2 disabled:opacity-40"
    >
      <legend className="px-1 text-2xs text-zinc-400">{label}</legend>
      {value.map((item, index) => (
        <div key={index} className="space-y-1 rounded border border-white/5 p-1.5">
          {renderItem(item, index, (next) => onValueChange(value.map((entry, at) => (at === index ? next : entry))))}
          <div className="flex justify-end gap-1 text-2xs text-muted-foreground">
            <IconButton
              variant="ghost"
              size="sm"
              label={`Move ${label} item ${index + 1} up`}
              disabled={disabled || index === 0}
              onClick={() => move(index, -1)}
            >
              <ArrowUp />
            </IconButton>
            <IconButton
              variant="ghost"
              size="sm"
              label={`Move ${label} item ${index + 1} down`}
              disabled={disabled || index === value.length - 1}
              onClick={() => move(index, 1)}
            >
              <ArrowDown />
            </IconButton>
            <Button
              variant="destructive"
              size="sm"
              aria-label={`Remove ${label} item ${index + 1}`}
              onClick={() => {
                onValueChange(value.filter((_, at) => at !== index));
                onValueCommit?.();
              }}
            >
              Remove
            </Button>
          </div>
        </div>
      ))}
      {!value.length && <p className="px-1 text-xs text-zinc-600">No items</p>}
      <div className="relative" data-terminal={addEndpoint ? terminalKey(addEndpoint, "input") : undefined}>
        {addEndpoint && !disabled && (
          <Terminal endpoint={addEndpoint} direction="input" className="absolute top-2 -left-4" />
        )}
        <Button
          variant="dashed"
          onClick={() => {
            onValueChange([...value, createItem()]);
            onValueCommit?.();
          }}
          className="w-full py-1.5 text-2xs"
        >
          <Plus />
          Add item
        </Button>
      </div>
    </fieldset>
  );
}

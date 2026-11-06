import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Plus, X } from "lucide-react";
import type { Endpoint } from "@/api/protocol";
import { SliderElement } from "../elements";
import { Terminal } from "../../graph/terminal";
import { ReferenceControl } from "./field-control";

export type BlendInput = { source: Endpoint | number | number[] | null; weight: number };

export function BlendControl({
  nodeId,
  value,
  onChange,
  onCommit,
  disabled,
}: {
  nodeId: string;
  value: BlendInput[];
  onChange: (value: BlendInput[]) => void;
  onCommit?: () => void;
  disabled: boolean;
}) {
  const update = (index: number, changes: Partial<BlendInput>) =>
    onChange(value.map((item, at) => (at === index ? { ...item, ...changes } : item)));
  return (
    <fieldset disabled={disabled} className="space-y-2 disabled:opacity-40">
      {value.map((item, index) => {
        const source =
          item.source !== null && typeof item.source === "object" && "nodeId" in item.source ? item.source : null;
        return (
          <div key={index} className="relative rounded-lg border border-border bg-black/15 px-2 py-1.5">
            <Terminal
              endpoint={{ nodeId, element: `input_${index}` }}
              direction="input"
              className="absolute top-4 -left-5"
            />
            <div className="flex items-center gap-2 text-2xs">
              <span className="min-w-0 flex-1 truncate text-zinc-300">
                {source ? `${source.nodeId} · ${source.element}` : `Input ${index + 1}`}
              </span>
              <IconButton
                variant="destructive"
                label={`Remove input ${index + 1}`}
                onClick={() => {
                  onChange(value.filter((_, at) => at !== index));
                  onCommit?.();
                }}
                disabled={disabled}
              >
                <X />
              </IconButton>
            </div>
            <SliderElement
              label="Weight"
              value={item.weight}
              min={0}
              max={10}
              step={0.01}
              disabled={disabled}
              onValueChange={(weight) => update(index, { weight })}
              onValueCommit={onCommit}
            />
            <details open={!source} className="text-2xs text-muted-foreground">
              <summary className="cursor-pointer">Source</summary>
              <ReferenceControl
                nodeId={nodeId}
                field={{ name: "source", label: "Source", control: "reference" }}
                value={source}
                disabled={disabled}
                onChange={(source) => {
                  update(index, {
                    source: source?.element ? { nodeId: source.nodeId, element: source.element } : null,
                  });
                  onCommit?.();
                }}
              />
            </details>
          </div>
        );
      })}
      <div className="relative">
        <Terminal endpoint={{ nodeId, element: "add_element" }} direction="input" className="absolute top-2 -left-5" />
        <Button
          variant="dashed"
          disabled={disabled}
          onClick={() => {
            onChange([...value, { source: null, weight: 1 }]);
            onCommit?.();
          }}
          className="w-full"
        >
          <Plus />
          Add input · or drop a wire
        </Button>
      </div>
    </fieldset>
  );
}

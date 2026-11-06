import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Plus, X } from "lucide-react";
import { useGraph } from "@/api/hooks";
import type { ClusteringInput } from "@/features/nodes/clustering";
import { IntervalElement, SelectElement } from "../elements";
import { Terminal } from "../../graph/terminal";

export function ClusteringControl({
  nodeId,
  value,
  onChange,
  onCommit,
  disabled,
}: {
  nodeId: string;
  value: ClusteringInput[];
  onChange: (value: ClusteringInput[]) => void;
  onCommit?: () => void;
  disabled: boolean;
}) {
  const snapshot = useGraph();
  const sources = (snapshot?.nodes ?? [])
    .filter((node) => node.id !== nodeId)
    .flatMap((node) =>
      node.ports
        .filter((port) => port.direction === "out" && port.shape.length === 1 && port.shape[0] === 1)
        .map((port) => ({
          value: JSON.stringify({ nodeId: node.id, element: port.name }),
          label: `${node.id} · ${port.name}`,
        })),
    );
  const update = (index: number, changes: Partial<ClusteringInput>) =>
    onChange(value.map((item, at) => (at === index ? { ...item, ...changes } : item)));
  return (
    <fieldset disabled={disabled} className="space-y-2 disabled:opacity-40">
      {value.map((item, index) => (
        <div key={index} className="relative rounded-lg border border-border bg-black/15 px-2 py-1.5">
          <Terminal
            endpoint={{ nodeId, element: `input_${index}` }}
            direction="input"
            className="absolute top-4 -left-5"
          />
          <div className="flex items-center gap-2 text-2xs">
            <span className={index % 2 ? "text-cyan-300" : "text-violet-300"}>
              {index + 1} · {index % 2 ? "V" : "H"}
            </span>
            <span
              className="min-w-0 flex-1 truncate text-zinc-300"
              title={item.source ? `${item.source.nodeId}.${item.source.element}` : undefined}
            >
              {item.source ? `${item.source.nodeId} · ${item.source.element}` : `Parameter ${index + 1}`}
            </span>
            <IconButton
              variant="destructive"
              label={`Remove parameter ${index + 1}`}
              onClick={() => {
                onChange(value.filter((_, at) => at !== index));
                onCommit?.();
              }}
              disabled={disabled}
            >
              <X />
            </IconButton>
          </div>
          <details open={!item.source} className="text-2xs text-muted-foreground">
            <summary className="cursor-pointer">
              {item.interval[0]} → {item.interval[1]} · Edit
            </summary>
            <div className="space-y-1 pt-1">
              <SelectElement
                label="Source"
                value={item.source ? JSON.stringify(item.source) : "none"}
                disabled={disabled}
                options={[{ value: "none", label: "Choose scalar source…" }, ...sources]}
                onValueChange={(source) => {
                  update(index, { source: source === "none" ? null : JSON.parse(source) });
                  onCommit?.();
                }}
              />
              <IntervalElement
                label="Start / end"
                value={item.interval}
                min={-1000000}
                max={1000000}
                ordered={false}
                onValueChange={(interval) => update(index, { interval })}
                onValueCommit={onCommit}
                disabled={disabled}
              />
            </div>
          </details>
        </div>
      ))}
      {!value.length && (
        <p className="px-1 py-2 text-2xs text-muted-foreground">Add a parameter or drop a scalar wire below.</p>
      )}
      <div className="relative">
        <Terminal endpoint={{ nodeId, element: "add_element" }} direction="input" className="absolute top-2 -left-5" />
        <Button
          variant="dashed"
          disabled={disabled}
          onClick={() => {
            onChange([...value, { source: null, interval: [0, 1] }]);
            onCommit?.();
          }}
          className="w-full"
        >
          <Plus />
          Add parameter
        </Button>
      </div>
    </fieldset>
  );
}

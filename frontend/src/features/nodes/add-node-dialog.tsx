import { X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Dialog, DialogClose, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useBackend } from "@/api/backend-context";
import { useGraph } from "@/api/hooks";
import type { NodeDescriptor, Endpoint } from "@/api/protocol";
import { TextElement } from "./elements";
import { FieldControl, ReferenceControl } from "./forms/field-control";
import { completeConfiguration } from "./configuration";
import { useCatalog } from "../catalog/catalog-context";
import { availableNodeName } from "./node-name";

export function AddNodeDialog({ onClose, position }: { onClose: () => void; position: [number, number] }) {
  const backend = useBackend();
  const dialog = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const snapshot = useGraph();
  const catalog = useCatalog();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [type, setType] = useState("");
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const choices = Object.values(catalog)
    .filter((item) => `${item.type} ${item.title} ${item.category}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => a.category.localeCompare(b.category) || a.title.localeCompare(b.title));
  const folders = new Map<string, { type: string; index: number }[]>();
  choices.forEach((item, index) => {
    const folder = item.category;
    if (!folders.has(folder)) folders.set(folder, []);
    folders.get(folder)!.push({ type: item.type, index });
  });
  const definition = catalog[type];
  const automaticName = type
    ? availableNodeName(definition.title, snapshot?.graph.nodes.map((node) => node.id) ?? [])
    : "";
  useEffect(() => {
    dialog.current?.querySelector("[data-selected=true]")?.scrollIntoView({ block: "nearest" });
  }, [selected, type, query]);
  // A type's default descriptor never changes while the backend runs.
  const prototype = useQuery({
    queryKey: ["node-type", type],
    queryFn: () => backend.graph.describeType(type),
    enabled: Boolean(type),
    staleTime: Infinity,
  }).data;
  const node: NodeDescriptor | null = prototype ? { ...(prototype as NodeDescriptor), id: "" } : null;
  function choose(next: string) {
    if (next === type) return;
    setType(next);
    setParameters({});
    setError("");
  }
  async function create() {
    setBusy(true);
    setError("");
    const nodeId = name.trim() || automaticName;
    const values = { ...parameters };
    for (const field of definition.fields.filter((field) => field.control === "shape")) {
      values[field.name] ??= node!.elements.find((element) => element.name === field.name)!.value;
    }
    const connections = definition.fields
      .filter((field) => field.control === "port")
      .flatMap((field) => {
        const source = values[field.name] as Endpoint | null;
        delete values[field.name];
        return source ? [{ id: crypto.randomUUID(), source, target: { nodeId, element: field.name } }] : [];
      });
    try {
      const result = await backend.graph.addNode({ nodeId, nodeType: type, parameters: values, connections, position });
      if (result) onClose();
      else setError(backend.status.error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        ref={dialog}
        aria-describedby={undefined}
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          search.current!.focus();
        }}
        // A stray click outside must not discard a half-filled node form.
        onInteractOutside={(event) => event.preventDefault()}
        className="max-h-[85vh] w-[min(90vw,420px)] overflow-y-auto"
      >
        <div className="mb-4 flex items-center justify-between">
          <DialogTitle className="text-sm font-semibold">{type ? definition.title : "Add node"}</DialogTitle>
          <DialogClose type="button" aria-label="Close add node" className="text-muted-foreground">
            <X className="size-4" />
          </DialogClose>
        </div>
        {!type ? (
          <>
            <input
              ref={search}
              aria-label="Search nodes"
              placeholder="Search nodes…"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setSelected(0);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault();
                  setSelected((index) =>
                    Math.max(0, Math.min(choices.length - 1, index + (event.key === "ArrowDown" ? 1 : -1))),
                  );
                }
                if (event.key === "Enter" && choices[selected]) {
                  event.preventDefault();
                  choose(choices[selected].type);
                }
              }}
              className="mb-3 w-full rounded-lg border border-border bg-black/20 p-3 text-sm outline-none focus:border-violet-400"
            />
            <div className="max-h-80 space-y-1 overflow-y-auto">
              {[...folders].map(([folder, items]) => (
                <details
                  key={folder}
                  open={Boolean(query) || items.some((item) => item.index === selected)}
                  className="rounded-lg border border-white/5 bg-black/10"
                >
                  <summary className="cursor-pointer px-3 py-2 text-xs text-zinc-300">
                    <span className="ml-1 capitalize">{folder}</span>
                    <span className="ml-2 text-2xs text-muted-foreground">{items.length}</span>
                  </summary>
                  <div className="space-y-0.5 px-2 pb-2">
                    {items.map((item) => (
                      <button
                        key={item.type}
                        type="button"
                        data-selected={selected === item.index}
                        onClick={() => choose(item.type)}
                        className={`block w-full rounded-md px-3 py-2 text-left text-xs ${selected === item.index ? "bg-violet-400/15 text-violet-200" : "text-zinc-400 hover:bg-white/5"}`}
                      >
                        {catalog[item.type].title}
                      </button>
                    ))}
                  </div>
                </details>
              ))}
              {!choices.length && <p className="p-3 text-xs text-muted-foreground">No matching nodes.</p>}
            </div>
          </>
        ) : (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void create();
            }}
            className="space-y-3"
          >
            <p className="text-xs text-zinc-400">{definition.description}</p>
            <TextElement label="Name" value={name} onValueChange={setName} placeholder={automaticName} />
            {!node ? (
              <p className="text-xs text-muted-foreground">Loading parameters…</p>
            ) : (
              definition.fields
                .filter((field) => !field.hidden && field.control !== "managed")
                .map((field) => {
                  const element = node.elements.find((item) => item.name === field.name);
                  if (!element) return null;
                  const value = Object.hasOwn(parameters, field.name) ? parameters[field.name] : element.value;
                  const onChange = (value: unknown) =>
                    setParameters((previous) => {
                      const next = { ...previous, [field.name]: value };
                      if (
                        value &&
                        field.control === "port" &&
                        node.ports.some((port) => port.name === field.name && port.adaptiveShape)
                      ) {
                        const source = value as Endpoint;
                        next.shape = snapshot!.nodes
                          .find((item) => item.id === source.nodeId)!
                          .ports.find((port) => port.name === source.element)!.shape;
                      }
                      return next;
                    });
                  const count = field.bounds
                    ? Number(
                        parameters[field.bounds.from] ??
                          node.elements.find((item) => item.name === field.bounds!.from)?.value,
                      )
                    : 0;
                  return (
                    <div key={field.name}>
                      {field.control === "port" ? (
                        <ReferenceControl
                          nodeId={node.id}
                          field={field}
                          value={(parameters[field.name] ?? null) as Endpoint | null}
                          onChange={onChange}
                        />
                      ) : (
                        <FieldControl
                          node={node}
                          field={field}
                          parameters={parameters}
                          onParametersChange={(values) => setParameters((previous) => ({ ...previous, ...values }))}
                          element={
                            field.bounds
                              ? {
                                  ...element,
                                  min: Math.floor(count * field.bounds.min),
                                  max: Math.floor(count * field.bounds.max),
                                }
                              : element
                          }
                          value={value}
                          onChange={onChange}
                        />
                      )}
                    </div>
                  );
                })
            )}
            {error && (
              <p role="alert" className="text-xs text-rose-300">
                {error}
              </p>
            )}
            <div className="flex justify-between gap-2 pt-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setType("");
                  setName("");
                }}
                className="text-xs text-zinc-400"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={busy || !node || !completeConfiguration(definition.fields, parameters)}
                className="rounded-lg bg-violet-400/20 px-4 py-2 text-xs text-violet-200 disabled:opacity-40"
              >
                {busy ? "Creating…" : "Create node"}
              </button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

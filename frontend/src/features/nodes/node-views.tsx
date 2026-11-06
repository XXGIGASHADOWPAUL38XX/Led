import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useBackend } from "@/api/backend-context";
import { useQuery } from "@tanstack/react-query";
import { usePlayer, useViewSettings } from "@/api/hooks";
import { type NodeDescriptor } from "@/api/protocol";
import type { ViewDefinition } from "./definition";
import { viewKey, type ViewSettings } from "@/api/template";
import { ColorElement, DataElement, IntervalElement, PlaylistPlayer, SliderElement, TextElement } from "./elements";
import { StreamCanvas } from "../streams/stream-canvas";
import { seriesColor } from "../streams/canvas-renderer";
import type { ClusteringInput } from "./clustering";

function StreamView({ node, view }: { node: NodeDescriptor; view: ViewDefinition }) {
  const backend = useBackend();
  const settings = useViewSettings(node.id, viewKey(view.kind, view.data));
  const setSettings = (changes: Partial<ViewSettings>) =>
    backend.setViewSettings(node.id, viewKey(view.kind, view.data), changes);
  const title = settings.title ?? view.label ?? view.data!;
  const range: [number, number] = settings.range ?? [0, 1];
  const shape = node.ports.find((port) => port.name === view.data)!.shape;
  const dimensions = view.kind === "scatter" ? shape.at(-1)! : 0;
  const rows = view.series?.length ?? (view.kind === "history" && shape.length > 1 ? Math.min(shape[0], 8) : 1);
  const legend = view.kind === "history" || rows > 1;
  const expanded = settings.expanded ?? true;
  return (
    <div className="space-y-2">
      <details
        open={expanded}
        onToggle={(event) => {
          if (event.currentTarget.open !== expanded) setSettings({ expanded: event.currentTarget.open });
        }}
        className="overflow-hidden rounded-lg border border-border bg-black/20"
      >
        <summary className="cursor-pointer px-3 py-2 text-2xs text-zinc-400">{title}</summary>
        {expanded && (
          <StreamCanvas
            key={JSON.stringify([node.id, view.kind, view.data, view.status, dimensions])}
            nodeId={node.id}
            view={view}
            settings={settings}
            title={title}
            dimensions={dimensions}
            inputs={
              view.kind === "clustering"
                ? (node.elements.find((element) => element.name === "inputs")?.value as ClusteringInput[])
                : undefined
            }
          />
        )}
        {view.kind === "bars" && (
          <div className="flex justify-between px-3 pb-2 font-mono text-[9px] text-muted-foreground">
            <span>
              {view.xMinField ? Number(node.elements.find((field) => field.name === view.xMinField)?.value) : 0}{" "}
              {view.unit}
            </span>
            <span>
              {view.xMaxField
                ? Number(node.elements.find((field) => field.name === view.xMaxField)?.value)
                : Math.max(1, shape.reduce((a, b) => a * b, 1) - 1)}{" "}
              {view.unit}
            </span>
          </div>
        )}
      </details>
      {legend && (
        <div aria-label="Chart legend" className="flex flex-wrap gap-2 px-1">
          {Array.from({ length: rows }, (_, row) => {
            const id = String(row),
              hidden = settings.hiddenSeries ?? [];
            return (
              <button
                key={id}
                type="button"
                aria-pressed={!hidden.includes(id)}
                className="text-2xs"
                style={{ color: seriesColor(settings, row), opacity: hidden.includes(id) ? 0.4 : 1 }}
                onClick={() =>
                  setSettings({
                    hiddenSeries: hidden.includes(id) ? hidden.filter((item) => item !== id) : [...hidden, id],
                  })
                }
              >
                {view.series?.[row] ?? `Channel ${row + 1}`}
              </button>
            );
          })}
        </div>
      )}
      <details className="px-1 text-2xs text-muted-foreground">
        <summary className="cursor-pointer">Display settings</summary>
        <div className="mt-2 space-y-2">
          <TextElement label="Title" value={title} onValueChange={(title) => setSettings({ title })} />
          {(view.kind === "meter" || view.kind === "scatter") && (
            <SliderElement
              label={view.kind === "scatter" ? "Trail samples" : "History samples"}
              value={settings.historyLength ?? 100}
              onValueChange={(historyLength) => setSettings({ historyLength })}
              min={10}
              max={1000}
            />
          )}
          {legend &&
            Array.from({ length: rows }, (_, row) => (
              <ColorElement
                key={row}
                label={view.series?.[row] ?? `Line ${row + 1}`}
                value={settings.lineColors?.[row] ?? [167, 139, 250]}
                onValueChange={(color) => setSettings({ lineColors: { ...settings.lineColors, [row]: color } })}
              />
            ))}
          {dimensions > 3 &&
            Array.from({ length: dimensions }, (_, index) => (
              <IntervalElement
                key={index}
                label={`Dimension ${index + 1}`}
                value={settings.axisRanges?.[String(index)] ?? range}
                min={-1000000}
                max={1000000}
                ordered={false}
                onValueChange={(interval) => {
                  if (interval[0] !== interval[1])
                    setSettings({ axisRanges: { ...settings.axisRanges, [index]: interval } });
                }}
              />
            ))}
          {view.kind !== "color" && view.kind !== "trigger" && view.kind !== "clustering" && view.kind !== "angle" && (
            <>
              {dimensions <= 3 && (
                <IntervalElement
                  label={view.kind === "scatter" ? (dimensions === 3 ? "X / Y / Z range" : "X / Y range") : "Y range"}
                  value={[range[0], range[1]]}
                  min={-10000}
                  max={10000}
                  onValueChange={([low, high]) => {
                    if (low < high) setSettings({ range: [low, high] });
                  }}
                />
              )}
              <Button variant="link" size="inline" onClick={() => setSettings({ range: null, axisRanges: {} })}>
                Auto range
              </Button>
            </>
          )}
        </div>
      </details>
    </div>
  );
}

function LivePlaylist({ nodeId }: { nodeId: string }) {
  const backend = useBackend();
  const player = usePlayer(nodeId);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  // Each submitted query is cached per player; search runs on the backend, which also vets what can be queued.
  const search = useQuery({
    queryKey: ["player-search", nodeId, submitted],
    queryFn: () => backend.playback.search(nodeId, submitted),
    enabled: Boolean(submitted),
    staleTime: 60_000,
  });
  return (
    <div className="space-y-2">
      <Button
        disabled={player?.loading && !player.tracks.some((track) => track.loaded)}
        onClick={() => {
          void backend.playback.play(nodeId);
        }}
      >
        {player?.loading && !player.tracks.length ? "Loading playlist…" : "Load playlist / play"}
      </Button>
      <PlaylistPlayer
        loading={player?.loading ?? false}
        tracks={player?.tracks ?? []}
        activeTrackId={player?.activeTrackId ?? null}
        playing={player?.playing ?? false}
        position={player?.position ?? 0}
        duration={player?.duration ?? 0}
        onPlay={(trackId) => {
          void backend.playback.play(nodeId, trackId);
        }}
        onPause={() => {
          void backend.playback.pause(nodeId);
        }}
        onSeek={(position) => backend.playback.seek(nodeId, position)}
        onAdd={(track) => {
          void backend.playback.queue(nodeId, track.id);
        }}
        onRemove={(trackId) => {
          void backend.playback.unqueue(nodeId, trackId);
        }}
        query={query}
        onQueryChange={setQuery}
        searching={search.isFetching}
        results={search.data?.tracks ?? null}
        onSearch={setSubmitted}
      />
    </div>
  );
}

export function NodeView({
  node,
  view,
  hidePort = false,
}: {
  node: NodeDescriptor;
  view: ViewDefinition;
  hidePort?: boolean;
}) {
  const backend = useBackend();
  const settings = useViewSettings(node.id, viewKey(view.kind, view.data));
  const open = settings.open ?? view.open ?? false;
  if (view.kind === "playlist") return <LivePlaylist nodeId={node.id} />;
  const port = node.ports.find((port) => port.name === view.data);
  if (!port) return null;
  return (
    <div className="space-y-2 border-t border-white/5 pt-2">
      {!hidePort && (
        <DataElement
          label={view.label ?? port.name}
          endpoint={{ nodeId: node.id, element: port.name }}
          direction={port.direction === "out" ? "output" : "input"}
          shape={port.shape}
          unit={view.unit}
        />
      )}
      <Button
        variant="link"
        size="inline"
        aria-expanded={open}
        onClick={() => backend.setViewSettings(node.id, viewKey(view.kind, view.data), { open: !open })}
        className="text-2xs"
      >
        {open ? "Hide view" : "Show view"}
      </Button>
      {open && <StreamView node={node} view={view} />}
    </div>
  );
}

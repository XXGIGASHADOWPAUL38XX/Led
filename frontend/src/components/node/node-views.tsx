"use client";

import { useState } from "react";
import { backend } from "@/lib/backend/store";
import { usePlayer, useSearchResults, useViewSettings } from "@/lib/backend/hooks";
import { type NodeDescriptor } from "@/lib/backend/protocol";
import type { ViewDefinition } from "./definition";
import { viewKey, type ViewSettings } from "@/lib/backend/template";
import { ColorElement, DataElement, IntervalElement, PlaylistPlayer, SliderElement, TextElement } from "../elements";
import { StreamCanvas } from "../visualizations/stream-canvas";
import { seriesColor } from "../visualizations/canvas-renderer";

function StreamView({ node, view }: { node: NodeDescriptor; view: ViewDefinition }) {
  const settings = useViewSettings(node.id, viewKey(view.kind, view.data));
  const setSettings = (changes: Partial<ViewSettings>) => backend.setViewSettings(node.id, viewKey(view.kind, view.data), changes);
  const title = settings.title ?? view.label ?? view.data!;
  const range = settings.range ?? [0, 1];
  const shape = node.ports.find((port) => port.name === view.data)!.shape;
  const rows = view.series?.length ?? (view.kind === "history" && shape.length > 1 ? Math.min(shape[0], 8) : 1);
  const legend = view.kind === "history" || rows > 1;
  const expanded = settings.expanded ?? true;
  return <div className="space-y-2">
    <details open={expanded} onToggle={(event) => { if (event.currentTarget.open !== expanded) setSettings({ expanded: event.currentTarget.open }); }} className="overflow-hidden rounded-lg border border-white/10 bg-black/20">
      <summary className="cursor-pointer px-3 py-2 text-[10px] text-zinc-400">{title}</summary>
      {expanded && <StreamCanvas nodeId={node.id} view={view} settings={settings} title={title} />}
      {view.kind === "bars" && <div className="flex justify-between px-3 pb-2 font-mono text-[9px] text-zinc-500">
        <span>{view.xMinField ? Number(node.elements.find((field) => field.name === view.xMinField)?.value) : 0} {view.unit}</span>
        <span>{view.xMaxField ? Number(node.elements.find((field) => field.name === view.xMaxField)?.value) : Math.max(1, shape.reduce((a, b) => a * b, 1) - 1)} {view.unit}</span>
      </div>}
    </details>
    {legend && <div aria-label="Chart legend" className="flex flex-wrap gap-2 px-1">{Array.from({ length: rows }, (_, row) => {
      const id = String(row), hidden = settings.hiddenSeries ?? [];
      return <button key={id} type="button" aria-pressed={!hidden.includes(id)} className="text-[10px]" style={{ color: seriesColor(settings, row), opacity: hidden.includes(id) ? 0.4 : 1 }}
        onClick={() => setSettings({ hiddenSeries: hidden.includes(id) ? hidden.filter((item) => item !== id) : [...hidden, id] })}>{view.series?.[row] ?? `Channel ${row + 1}`}</button>;
    })}</div>}
    <details className="px-1 text-[10px] text-zinc-500"><summary className="cursor-pointer">Display settings</summary><div className="mt-2 space-y-2">
      <TextElement label="Title" value={title} onValueChange={(title) => setSettings({ title })} />
      {view.kind === "meter" && <SliderElement label="History samples" value={settings.historyLength ?? 100} onValueChange={(historyLength) => setSettings({ historyLength })} min={10} max={1000} />}
      {legend && Array.from({ length: rows }, (_, row) => <ColorElement key={row} label={view.series?.[row] ?? `Line ${row + 1}`} value={settings.lineColors?.[row] ?? [167, 139, 250]}
        onValueChange={(color) => setSettings({ lineColors: { ...settings.lineColors, [row]: color } })} />)}
      {view.kind !== "color" && view.kind !== "trigger" && <><IntervalElement label="Y range" value={[range[0], range[1]]} min={-10000} max={10000} onValueChange={([low, high]) => { if (low < high) setSettings({ range: [low, high] }); }} />
        <button type="button" className="px-1 text-violet-300" onClick={() => setSettings({ range: null })}>Auto range</button></>}
    </div></details>
  </div>;
}

function LivePlaylist({ nodeId }: { nodeId: string }) {
  const player = usePlayer(nodeId);
  const results = useSearchResults(nodeId);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const send = (type: string, payload: Record<string, unknown> = {}) => backend.command(type, { nodeId, ...payload });
  return <div className="space-y-2">
    <button type="button" onClick={() => { void send("player.play"); }} className="rounded bg-violet-400/15 px-3 py-1.5 text-xs text-violet-200">Load playlist / play</button>
    <PlaylistPlayer tracks={player?.tracks ?? []} activeTrackId={player?.activeTrackId ?? null} playing={player?.playing ?? false} position={player?.position ?? 0} duration={player?.duration ?? 0}
      onPlay={(trackId) => { void send("player.play", { trackId }); }} onPause={() => { void send("player.pause"); }} onSeek={(position) => send("player.seek", { position })}
      onAdd={(track) => { void send("playlist.add", { trackId: track.id }); }} onRemove={(trackId) => { void send("playlist.remove", { trackId }); }}
      query={query} onQueryChange={setQuery} searching={searching} results={results?.tracks ?? null}
      onSearch={(query) => { setSearching(true); void send("player.search", { query }).finally(() => setSearching(false)); }} />
  </div>;
}

export function NodeView({ node, view }: { node: NodeDescriptor; view: ViewDefinition }) {
  const settings = useViewSettings(node.id, viewKey(view.kind, view.data));
  const open = settings.open ?? view.open ?? false;
  if (view.kind === "playlist") return <LivePlaylist nodeId={node.id} />;
  const port = node.ports.find((port) => port.name === view.data);
  if (!port) return null;
  return <div className="space-y-2 border-t border-white/5 pt-2">
    <DataElement label={view.label ?? port.name} endpoint={{ nodeId: node.id, element: port.name }} direction={port.direction === "out" ? "output" : "input"} shape={port.shape} unit={view.unit} />
    <button type="button" aria-expanded={open} onClick={() => backend.setViewSettings(node.id, viewKey(view.kind, view.data), { open: !open })} className="px-1 text-[10px] text-violet-300">{open ? "Hide view" : "Show view"}</button>
    {open && <StreamView node={node} view={view} />}
  </div>;
}

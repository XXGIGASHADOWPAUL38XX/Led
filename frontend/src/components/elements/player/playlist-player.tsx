"use client";

import { MusicPlayer, formatTime, type MusicPlayerProps, type Track } from "./music-player";

export type PlaylistPlayerProps = Omit<MusicPlayerProps, "track" | "onPlay"> & {
  tracks: readonly Track[];
  activeTrackId: string | null;
  onPlay: (id: string) => void;
  onAdd: (track: Track) => void;
  onRemove: (id: string) => void;
  query: string;
  onQueryChange: (query: string) => void;
  onSearch: (query: string) => void;
  results: readonly Track[] | null;
  searching?: boolean;
  loading?: boolean;
  error?: string;
};

export function PlaylistPlayer({ tracks, activeTrackId, onPlay, onAdd, onRemove, query, onQueryChange, onSearch, results, searching = false, loading = false, error, ...player }: PlaylistPlayerProps) {
  const ready = tracks.filter((track) => track.loaded !== false).length;
  const activeTrack = tracks.find((track) => track.id === activeTrackId) ?? null;
  return (
    <div className="min-w-0 w-full space-y-3">
      <MusicPlayer key={activeTrackId} {...player} track={activeTrack} onPlay={() => { if (activeTrack) onPlay(activeTrack.id); }} />
      <form role="search" onSubmit={(event) => { event.preventDefault(); onSearch(query.trim()); }} className="flex flex-wrap gap-1.5">
        <input type="search" aria-label="Search music" placeholder="Find a track or artist…" value={query} onChange={(event) => onQueryChange(event.target.value)}
          className="h-8 min-w-32 flex-1 rounded-md border border-white/10 bg-black/20 px-2.5 text-xs text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-violet-400/70 focus:ring-2 focus:ring-violet-400/10" />
        <button type="submit" disabled={searching || !query.trim()}
          className="rounded-md border border-white/10 bg-white/5 px-2.5 text-[10px] text-zinc-300 transition-colors hover:bg-violet-400/15 focus-visible:outline-2 focus-visible:outline-violet-400 disabled:opacity-35">
          {searching ? "Searching…" : "Search"}
        </button>
      </form>
      {error && <p role="alert" className="text-xs text-rose-300">{error}</p>}
      {results !== null && (
        <section aria-label="Search results" aria-busy={searching} className="rounded-md border border-white/10 bg-black/10 p-1">
          {!results.length && <p role="status" className="px-2 py-3 text-[10px] text-zinc-500">{searching ? "Searching…" : "No tracks found."}</p>}
          <ul className="max-h-40 overflow-y-auto">
            {results.map((track) => {
              const added = tracks.some((item) => item.id === track.id);
              const downloading = track.downloadState === "downloading";
          const unavailable = track.loaded === false;
          return <li aria-busy={downloading} key={track.id} className="flex items-center gap-2 rounded p-2 hover:bg-white/5">
                <div className="min-w-0 flex-1"><p className="truncate text-xs text-zinc-200">{track.title}</p><p className="mt-0.5 truncate text-[10px] text-zinc-500">{track.artist}</p></div>
                <button type="button" disabled={added} onClick={() => onAdd(track)} aria-label={`Add ${track.title}`}
                  className="rounded px-1.5 py-1 text-violet-300 hover:bg-violet-400/15 focus-visible:outline-2 focus-visible:outline-violet-400 disabled:text-zinc-600"><span aria-hidden="true">{added ? "✓" : "+"}</span></button>
              </li>;
            })}
          </ul>
        </section>
      )}
      <div className="flex items-center justify-between px-1 text-[9px] uppercase tracking-widest text-zinc-500"><span>Queue</span><span>{ready} / {tracks.length} ready</span></div>
      <ul aria-label="Playlist" className="max-h-60 space-y-0.5 overflow-y-auto">
        {tracks.map((track, index) => {
          const selected = track.id === activeTrackId;
          const playing = selected && player.playing;
          const downloading = track.downloadState === "downloading";
          const unavailable = track.loaded === false;
          return <li aria-busy={downloading} key={track.id} className={`group/track flex items-center gap-1 rounded-md ${selected ? "bg-violet-400/10" : "hover:bg-white/5"}`}>
            <button type="button" disabled={unavailable} onClick={() => playing ? player.onPause() : onPlay(track.id)} aria-label={`${playing ? "Pause" : "Play"} ${track.title}`} aria-current={selected ? "true" : undefined}
              className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-2.5 text-left disabled:cursor-default disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-violet-400">
              <span aria-hidden="true" className={`w-4 shrink-0 text-center font-mono text-[10px] ${selected ? "text-violet-300" : "text-zinc-600"}`}>{downloading ? <span role="status" aria-label={`Downloading ${track.title}`} className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-violet-300/25 border-t-violet-300" /> : playing ? "Ⅱ" : String(index + 1).padStart(2, "0")}</span>
              <span className="min-w-0 flex-1"><span className={`block truncate text-xs ${selected ? "text-violet-100" : "text-zinc-300"}`}>{track.title}</span><span className="mt-0.5 block truncate text-[10px] text-zinc-500">{track.artist}</span>{unavailable && <span className={`block text-[9px] ${track.downloadState === "failed" ? "text-rose-300" : "text-violet-300"}`}>{downloading ? "Downloading…" : track.downloadState === "failed" ? "Download failed" : loading ? "Waiting to download" : "Not downloaded"}</span>}</span>
              <span className="shrink-0 whitespace-nowrap font-mono text-[9px] tabular-nums text-zinc-500">{track.duration > 0 ? formatTime(track.duration) : "—:—"}</span>
            </button>
            <button type="button" onClick={() => onRemove(track.id)} aria-label={`Remove ${track.title}`}
              className="mr-1 rounded p-1.5 text-xs text-zinc-600 transition-colors hover:bg-rose-400/10 hover:text-rose-300 focus-visible:outline-2 focus-visible:outline-violet-400">×</button>
          </li>;
        })}
      </ul>
      {loading && <p role="status" className="flex items-center justify-center gap-2 text-[10px] text-violet-300"><span aria-hidden="true" className="h-3 w-3 animate-spin rounded-full border-2 border-violet-300/25 border-t-violet-300" />{tracks.length ? "Downloading playlist… Play any ready track." : "Loading playlist…"}</p>}
      {!loading && !tracks.length && <p className="py-4 text-center text-xs text-zinc-500">Search for music to start your playlist.</p>}
    </div>
  );
}

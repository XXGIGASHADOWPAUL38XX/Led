"use client";

import * as Slider from "@radix-ui/react-slider";
import { useState } from "react";

export type Track = { id: string; title: string; artist: string; duration: number; loaded?: boolean; downloadState?: "queued" | "downloading" | "ready" | "failed" };

export function formatTime(seconds: number) {
  const total = Math.floor(Math.max(0, Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export type MusicPlayerProps = {
  track: Track | null;
  playing: boolean;
  position: number;
  duration: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (seconds: number) => void | Promise<unknown>;
};

export function MusicPlayer({ track, playing, position, duration, onPlay, onPause, onSeek }: MusicPlayerProps) {
  const [seeking, setSeeking] = useState<number | null>(null);
  const [committing, setCommitting] = useState(false);
  const elapsed = Math.max(0, seeking ?? position);
  async function commit(seconds: number) {
    setCommitting(true);
    try { await onSeek(seconds); }
    finally { setSeeking(null); setCommitting(false); }
  }
  return (
    <section aria-label="Music player" className="@container min-w-0 w-full rounded-lg border border-violet-400/20 bg-gradient-to-br from-violet-400/10 to-black/10 p-3">
      <div className="mb-3 flex min-w-0 items-center gap-2">
        <span aria-hidden="true" className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-violet-300/15 bg-violet-400/10 text-xl text-violet-200 @min-[18rem]:flex">♪</span>
        <div className="min-w-0 flex-1">
          <p className="line-clamp-2 break-words text-xs font-medium text-zinc-100" title={track?.title}>{track?.title ?? "Choose a track"}</p>
          <p className="mt-1 truncate text-[10px] text-zinc-400" title={track?.artist}>{track?.artist ?? "Your playlist is ready"}</p>
        </div>
        <button type="button" disabled={!track || track.loaded === false} onClick={playing ? onPause : onPlay}
          aria-label={playing ? "Pause" : "Play"} aria-pressed={playing}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-violet-400 text-sm text-[#181322] shadow-lg shadow-violet-500/10 transition-colors hover:bg-violet-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-200 disabled:cursor-default disabled:opacity-30">
          <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span>
        </button>
      </div>
      <Slider.Root min={0} max={Math.max(1, duration)} step={0.1} value={[duration > 0 ? Math.min(duration, elapsed) : 0]} onValueChange={([value]) => setSeeking(value)}
        onValueCommit={([value]) => { void commit(value); }} onPointerCancel={() => setSeeking(null)}
        disabled={committing || !track || track.loaded === false || duration <= 0} className="group/seek relative flex h-6 w-full touch-none select-none items-center">
        <Slider.Track className="relative h-1 w-full overflow-hidden rounded-full bg-white/10">
          <Slider.Range className="absolute h-full rounded-full bg-violet-400" />
        </Slider.Track>
        <Slider.Thumb aria-label="Playback position" aria-valuetext={`${formatTime(elapsed)} of ${formatTime(duration)}`}
          className="block h-3 w-3 rounded-full bg-violet-200 shadow focus:outline-2 focus:outline-offset-2 focus:outline-violet-400" />
      </Slider.Root>
      <div className="flex justify-between gap-2 font-mono text-[10px] tabular-nums text-zinc-400"><span>{formatTime(elapsed)}</span><span>{duration > 0 ? formatTime(duration) : "—:—"}</span></div>
    </section>
  );
}

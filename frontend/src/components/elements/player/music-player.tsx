"use client";

import * as Slider from "@radix-ui/react-slider";

export type Track = { id: string; title: string; artist: string; duration: number };

export function formatTime(seconds: number) {
  const total = Math.floor(Math.max(0, Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export type MusicPlayerProps = {
  track: Track | null;
  playing: boolean;
  position: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (seconds: number) => void;
};

export function MusicPlayer({ track, playing, position, onPlay, onPause, onSeek }: MusicPlayerProps) {
  const duration = track?.duration ?? 0;
  const elapsed = Math.min(duration, Math.max(0, position));
  return (
    <section aria-label="Music player" className="rounded-lg border border-violet-400/20 bg-gradient-to-br from-violet-400/10 to-black/10 p-3">
      <div className="mb-4 flex items-center gap-3">
        <span aria-hidden="true" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-violet-300/15 bg-violet-400/10 text-xl text-violet-200">♪</span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-zinc-100" title={track?.title}>{track?.title ?? "Choose a track"}</p>
          <p className="mt-1 truncate text-[10px] text-zinc-400">{track?.artist ?? "Your playlist is ready"}</p>
        </div>
        <button type="button" disabled={!track} onClick={playing ? onPause : onPlay}
          aria-label={playing ? "Pause" : "Play"} aria-pressed={playing}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-violet-400 text-sm text-[#181322] shadow-lg shadow-violet-500/10 transition-colors hover:bg-violet-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-200 disabled:cursor-default disabled:opacity-30">
          <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span>
        </button>
      </div>
      <Slider.Root min={0} max={Math.max(1, duration)} step={0.1} value={[elapsed]} onValueChange={([value]) => onSeek(value)}
        disabled={!track || duration <= 0} className="group/seek relative flex h-4 w-full touch-none select-none items-center">
        <Slider.Track className="relative h-1 w-full overflow-hidden rounded-full bg-white/10">
          <Slider.Range className="absolute h-full rounded-full bg-violet-400" />
        </Slider.Track>
        <Slider.Thumb aria-label="Playback position" aria-valuetext={`${formatTime(elapsed)} of ${formatTime(duration)}`}
          className="block h-2.5 w-2.5 rounded-full bg-violet-200 opacity-0 shadow transition-opacity group-hover/seek:opacity-100 focus:opacity-100 focus:outline-2 focus:outline-offset-2 focus:outline-violet-400" />
      </Slider.Root>
      <div className="flex justify-between font-mono text-[9px] tabular-nums text-zinc-500"><span>{formatTime(elapsed)}</span><span>{formatTime(duration)}</span></div>
    </section>
  );
}

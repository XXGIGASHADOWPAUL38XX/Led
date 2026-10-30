"use client";

import { useState } from "react";
import { Node } from "../node/node";
import { PlaylistPlayer } from "../elements/player/playlist-player";
import type { Track } from "../elements/player/music-player";

const library: Track[] = [
  { id: "aurora", title: "Aurora Drift", artist: "Northern Lights", duration: 264 },
  { id: "tide", title: "Midnight Tide", artist: "Coastal", duration: 318 },
  { id: "pulse", title: "Slow Pulse", artist: "After Hours", duration: 243 },
  { id: "bloom", title: "Violet Bloom", artist: "Northern Lights", duration: 296 },
  { id: "echo", title: "Distant Echo", artist: "Coastal", duration: 351 },
];

export function PlaylistPreview() {
  const [tracks, setTracks] = useState(library.slice(0, 3));
  const [activeTrackId, setActiveTrackId] = useState<string | null>(library[0].id);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Track[] | null>(null);

  return (
    <Node id="playlist-1" title="Playlist" description="UI preview · sample tracks, no audio connected." outputs={["audio", "sample_rate", "enqueue_token"]}>
      <PlaylistPlayer tracks={tracks} activeTrackId={activeTrackId} playing={playing} position={position} duration={tracks.find((track) => track.id === activeTrackId)?.duration ?? 0}
        onPlay={(id) => { if (id !== activeTrackId) setPosition(0); setActiveTrackId(id); setPlaying(true); }}
        onPause={() => setPlaying(false)} onSeek={setPosition}
        onAdd={(track) => setTracks((current) => [...current, track])}
        onRemove={(id) => {
          setTracks((current) => current.filter((track) => track.id !== id));
          if (id === activeTrackId) { setActiveTrackId(null); setPlaying(false); setPosition(0); }
        }}
        query={query} onQueryChange={setQuery} results={results}
        onSearch={(text) => setResults(library.filter((track) => `${track.title} ${track.artist}`.toLowerCase().includes(text.toLowerCase())))} />
    </Node>
  );
}

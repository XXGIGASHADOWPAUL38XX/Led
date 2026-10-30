import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SCPlaylistPlayer",
  "title": "SCPlaylist Player",
  "description": "Download, cache, and control playback of a SoundCloud playlist.",
  "category": "player",
  "fields": [
    {
      "name": "playlist_url",
      "control": "text"
    },
    {
      "name": "browser",
      "control": "text"
    },
    {
      "name": "profile",
      "control": "text"
    },
    {
      "name": "prefetch_seconds",
      "control": "slider",
      "unit": "s"
    },
    {
      "name": "cache",
      "control": "switch"
    },
    {
      "name": "offline_pipelines",
      "control": "sequence",
      "item": "node",
      "nodeTypes": [
        "StemsRecognition"
      ]
    }
  ],
  "views": [
    {
      "kind": "playlist"
    },
    {
      "kind": "history",
      "data": "audio",
      "label": "Audio",
      "open": false
    },
    {
      "kind": "meter",
      "data": "sample_rate",
      "label": "Sample rate",
      "open": false
    },
    {
      "kind": "meter",
      "data": "enqueue_token",
      "label": "Enqueue token",
      "open": false
    }
  ]
} satisfies NodeDefinition;

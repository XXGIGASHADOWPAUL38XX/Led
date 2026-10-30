import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "StreamPlayer",
  "title": "Stream Player",
  "description": "Play stereo audio and expose channels-first blocks for analysis.",
  "category": "stream",
  "fields": [
    {
      "name": "audio_in",
      "control": "port"
    },
    {
      "name": "sample_rate_in",
      "control": "port",
      "unit": "Hz"
    },
    {
      "name": "enqueue_token",
      "control": "port"
    },
    {
      "name": "sample_rate",
      "control": "slider",
      "unit": "Hz",
      "rebuild": true
    },
    {
      "name": "chunk_size",
      "control": "slider",
      "rebuild": true
    },
    {
      "name": "user_callback",
      "control": "managed"
    }
  ],
  "views": [
    {
      "kind": "history",
      "data": "chunk",
      "label": "Chunk",
      "open": false
    }
  ],
  "actions": [
    "start",
    "stop"
  ]
} satisfies NodeDefinition;

import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "StreamMic",
  "title": "Stream Mic",
  "description": "Capture mono microphone blocks for audio processing.",
  "category": "stream",
  "fields": [
    {
      "name": "user_callback",
      "control": "managed"
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

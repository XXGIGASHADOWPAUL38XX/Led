import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Buffer",
  "title": "Buffer",
  "description": "Keep a rolling stereo audio window for FFT or other audio analysis.",
  "category": "buffer",
  "fields": [
    {
      "name": "indata",
      "control": "port"
    },
    {
      "name": "chunk_size",
      "control": "slider",
      "rebuild": true
    },
    {
      "name": "length",
      "control": "slider",
      "rebuild": true
    }
  ],
  "views": [
    {
      "kind": "bars",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;

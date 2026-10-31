import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Buffer",
  "title": "Buffer",
  "description": "Keep a rolling mono or multichannel audio window; input shape adapts when linked.",
  "category": "buffer",
  "fields": [
    {
      "name": "indata",
      "control": "port"
    },
    {
      "name": "shape",
      "control": "shape",
      "label": "Input shape",
      "rebuild": true
    },
    {
      "name": "chunk_size",
      "control": "slider",
      "rebuild": true,
      "hidden": true
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

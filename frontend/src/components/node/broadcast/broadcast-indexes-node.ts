import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BroadcastIndexesNode",
  "title": "Broadcast Indexes",
  "description": "Sample rows using normalized indexes, preserving RGB and other trailing dimensions.",
  "category": "broadcast",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "shape",
      "control": "shape",
      "label": "Input shape",
      "rebuild": true
    },
    {
      "name": "indexes",
      "control": "array"
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

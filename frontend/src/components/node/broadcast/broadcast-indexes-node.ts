import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BroadcastIndexesNode",
  "title": "Broadcast Indexes",
  "description": "Sample a vector using normalized positions.",
  "category": "broadcast",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
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

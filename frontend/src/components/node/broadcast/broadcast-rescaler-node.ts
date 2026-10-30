import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BroadcastRescalerNode",
  "title": "Broadcast Rescaler",
  "description": "Resize an array along its first axis by nearest lower-index sampling.",
  "category": "broadcast",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
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

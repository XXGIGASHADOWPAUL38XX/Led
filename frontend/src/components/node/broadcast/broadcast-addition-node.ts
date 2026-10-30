import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BroadcastAddition",
  "title": "Broadcast Addition",
  "description": "Blend two arrays for mixing colors or visual signals.",
  "category": "broadcast",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "secondary_data",
      "control": "port"
    },
    {
      "name": "level",
      "control": "slider"
    }
  ],
  "views": [
    {
      "kind": "meter",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;

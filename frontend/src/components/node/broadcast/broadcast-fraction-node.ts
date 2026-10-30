import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BroadcastFractionNode",
  "title": "Broadcast Fraction",
  "description": "Select a movable contiguous slice along the first array axis.",
  "category": "broadcast",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "fraction",
      "control": "slider"
    },
    {
      "name": "interval_input",
      "control": "interval",
      "label": "Input range",
      "min": -10000,
      "max": 10000
    },
    {
      "name": "input",
      "control": "slider"
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

import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BarGraphChart",
  "title": "Bar Graph Chart",
  "description": "Expose bar heights and per-bar RGBA colors to frontend subscribers.",
  "category": "visual",
  "fields": [
    {
      "name": "data",
      "control": "port"
    },
    {
      "name": "number_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "brushes",
      "control": "port"
    }
  ],
  "views": [
    {
      "kind": "lights",
      "data": "data",
      "colors": "brushes",
      "label": "Lights",
      "open": true
    }
  ]
} satisfies NodeDefinition;

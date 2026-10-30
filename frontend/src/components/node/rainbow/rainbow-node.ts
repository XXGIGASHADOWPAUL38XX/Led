import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Rainbow",
  "title": "Rainbow",
  "description": "Pass through or mirror an RGB gradient for a color strip.",
  "category": "rainbow",
  "fields": [
    {
      "name": "n_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "inv_fraction",
      "control": "slider"
    },
    {
      "name": "gradiant",
      "control": "port"
    },
    {
      "name": "mode",
      "control": "select"
    }
  ],
  "views": [
    {
      "kind": "color",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;

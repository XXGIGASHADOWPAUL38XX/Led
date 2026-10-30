import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SingleColor",
  "title": "Single Color",
  "description": "Generate a uniform RGB strip for coloring a visualization.",
  "category": "visual",
  "fields": [
    {
      "name": "color",
      "control": "color",
      "channels": [
        "color_red",
        "color_green",
        "color_blue"
      ]
    },
    {
      "name": "number_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "color_red",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_green",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_blue",
      "control": "port",
      "hidden": true
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

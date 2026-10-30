import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Gradiant",
  "title": "Gradiant",
  "description": "Generate a spatial RGB gradient by interpolating in HSV color space.",
  "category": "rainbow",
  "fields": [
    {
      "name": "n_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "color_in",
      "control": "color",
      "channels": [
        "color_in_red",
        "color_in_green",
        "color_in_blue"
      ]
    },
    {
      "name": "color_out",
      "control": "color",
      "channels": [
        "color_out_red",
        "color_out_green",
        "color_out_blue"
      ]
    },
    {
      "name": "cycle",
      "control": "slider"
    },
    {
      "name": "color_in_red",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_in_green",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_in_blue",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_out_red",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_out_green",
      "control": "port",
      "hidden": true
    },
    {
      "name": "color_out_blue",
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

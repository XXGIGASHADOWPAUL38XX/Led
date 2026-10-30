import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "CenterToEdge",
  "title": "Center To Edge",
  "description": "Turn a trigger pulse into a fading center-to-edge intensity profile.",
  "category": "groups",
  "fields": [
    {
      "name": "input_trigger",
      "control": "port"
    },
    {
      "name": "length",
      "control": "slider",
      "rebuild": true
    },
    {
      "name": "decay_length",
      "control": "slider",
      "scale": "logarithmic",
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

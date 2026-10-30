import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "EdgeToCenterTrigger",
  "title": "Edge To Center Trigger",
  "description": "Turn a trigger pulse into a fading edge-to-center intensity profile.",
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

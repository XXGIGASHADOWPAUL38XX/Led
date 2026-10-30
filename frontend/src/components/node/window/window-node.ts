import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Window",
  "title": "Window",
  "description": "Keep recent array frames with an editable input shape for temporal aggregation.",
  "category": "window",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "shape",
      "control": "shape",
      "label": "Input shape",
      "rebuild": true
    },
    {
      "name": "length",
      "control": "slider",
      "scale": "logarithmic",
      "rebuild": true
    },
    {
      "name": "init_value",
      "control": "slider"
    },
    {
      "name": "offset",
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

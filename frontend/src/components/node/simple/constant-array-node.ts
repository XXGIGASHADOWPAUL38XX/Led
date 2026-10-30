import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ConstantArray",
  "title": "Constant Array",
  "description": "Generate a constant vector for masks, levels, or array arithmetic.",
  "category": "simple",
  "fields": [
    {
      "name": "input_value",
      "control": "slider"
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

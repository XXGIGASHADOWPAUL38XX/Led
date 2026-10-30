import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Gathering",
  "title": "Gathering",
  "description": "Select enabled source values using a parallel boolean list.",
  "category": "routing",
  "fields": [
    {
      "name": "input_datas",
      "control": "sequence",
      "item": "reference"
    },
    {
      "name": "input_booleans",
      "control": "sequence",
      "item": "reference"
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

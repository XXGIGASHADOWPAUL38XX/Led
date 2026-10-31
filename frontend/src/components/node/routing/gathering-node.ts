import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Gathering",
  "title": "Gathering",
  "description": "Select the first enabled source using a matching list of enable signals.",
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

import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "MidSideEnergy",
  "title": "Mid Side Energy",
  "description": "Measure stereo center energy and stereo width.",
  "category": "features",
  "fields": [
    {
      "name": "buffer_data",
      "control": "port"
    },
    {
      "name": "length",
      "control": "slider",
      "rebuild": true
    }
  ],
  "views": [
    {
      "kind": "meter",
      "data": "mid_energy",
      "label": "Mid energy",
      "open": false
    },
    {
      "kind": "meter",
      "data": "side_energy",
      "label": "Side energy",
      "open": false
    },
    {
      "kind": "meter",
      "data": "mid_ratio",
      "label": "Mid ratio",
      "open": false
    },
    {
      "kind": "bars",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;

import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "AmplitudeLevelFunction",
  "title": "Amplitude Level Function",
  "description": "Provide a frequency-index gain curve to an amplitude transformer.",
  "category": "amplitudes",
  "fields": [
    {
      "name": "number_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "offset",
      "control": "slider"
    },
    {
      "name": "drop",
      "control": "slider"
    },
    {
      "name": "drop_center",
      "control": "slider",
      "bounds": {
        "from": "number_points",
        "min": 0,
        "max": 0.5
      }
    },
    {
      "name": "drop_width",
      "control": "slider"
    },
    {
      "name": "rise",
      "control": "slider"
    },
    {
      "name": "rise_center",
      "control": "slider",
      "bounds": {
        "from": "number_points",
        "min": 0.5,
        "max": 1
      }
    },
    {
      "name": "rise_width",
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

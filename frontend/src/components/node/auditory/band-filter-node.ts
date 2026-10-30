import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "BandFilter",
  "title": "Band Filter",
  "description": "Apply a first-order Butterworth band-pass filter to audio.",
  "category": "auditory",
  "fields": [
    {
      "name": "buffer_data",
      "control": "port"
    },
    {
      "name": "lowcut",
      "control": "slider",
      "unit": "Hz",
      "scale": "logarithmic"
    },
    {
      "name": "highcut",
      "control": "slider",
      "unit": "Hz",
      "scale": "logarithmic"
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

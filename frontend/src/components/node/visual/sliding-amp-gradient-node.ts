import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SlidingAmpGradientNode",
  "title": "Sliding Amp Gradient",
  "description": "Move an RGB gradient window according to spectral center frequency.",
  "category": "visual",
  "fields": [
    {
      "name": "input_frequencies",
      "control": "port"
    },
    {
      "name": "input_amplitudes",
      "control": "port"
    },
    {
      "name": "slide_window_fraction",
      "control": "slider",
      "rebuild": true
    },
    {
      "name": "slide_min_avg_amp",
      "control": "slider"
    },
    {
      "name": "slide_max_avg_amp",
      "control": "slider"
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

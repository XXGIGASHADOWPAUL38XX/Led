import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Amplitudes",
  "title": "Amplitudes",
  "description": "Convert an audio window to a logarithmically spaced spectrum.",
  "category": "amplitudes",
  "fields": [
    { "name": "shape", "control": "shape", "label": "Input shape", "rebuild": true },
    {
      "name": "buffer",
      "control": "port"
    },
    {
      "name": "min_frequency",
      "control": "slider",
      "label": "Min frequency",
      "unit": "Hz",
      "scale": "logarithmic"
    },
    {
      "name": "max_frequency",
      "control": "slider",
      "label": "Max frequency",
      "unit": "Hz"
    },
    {
      "name": "fft_size",
      "hidden": true,
      "control": "slider",
      "label": "FFT size",
      "rebuild": true
    },
    {
      "name": "freq_bins",
      "control": "slider",
      "label": "Bins",
      "rebuild": true
    },
    {
      "name": "powering",
      "control": "slider",
      "label": "Weighting"
    }
  ],
  "views": [
    {
      "kind": "bars",
      "data": "frequencies",
      "label": "Frequencies",
      "open": false
    },
    {
      "kind": "bars",
      "data": "data",
      "label": "Data",
      "open": true,
      "xScale": "logarithmic",
      "xMinField": "min_frequency",
      "xMaxField": "max_frequency",
      "unit": "Hz"
    }
  ]
} satisfies NodeDefinition;

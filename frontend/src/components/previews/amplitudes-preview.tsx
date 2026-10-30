"use client";

import { useState } from "react";
import { Node } from "../node/node";
import { DataElement } from "../elements/data-element";
import { SliderElement } from "../elements/slider-element";
import { BarChartElement } from "../elements/bar-chart-element";

export function AmplitudesPreview({ data }: { data?: readonly number[] }) {
  const [fftSize, setFftSize] = useState(2048);
  const [freqBins, setFreqBins] = useState(180);
  const [minFrequency, setMinFrequency] = useState(20);
  const [maxFrequency, setMaxFrequency] = useState(5000);
  const [powering, setPowering] = useState(0.5);

  // Deterministic display-only spectrum until a real signal is supplied.
  const preview = Array.from({ length: freqBins }, (_, index) => {
    const x = index / Math.max(1, freqBins - 1);
    return (8 + 36 * Math.exp(-(((x - 0.28) / 0.2) ** 2))) * (0.55 + 0.45 * Math.sin(index * 1.7) ** 2);
  });

  return (
    <Node id="amplitudes-1" title="Amplitudes" description="Shape a stereo frequency spectrum for lighting.">
      <DataElement label="Buffer" direction="input" shape={[2, fftSize]} />
      <SliderElement label="FFT size" value={fftSize} onValueChange={setFftSize} min={16} max={65536} />
      <SliderElement label="Bins" value={freqBins} onValueChange={setFreqBins} min={1} max={4096} />
      <SliderElement label="Min freq." value={minFrequency} onValueChange={setMinFrequency} min={20} max={maxFrequency - 1} scale="logarithmic" unit="Hz" />
      <SliderElement label="Max freq." value={maxFrequency} onValueChange={setMaxFrequency} min={minFrequency + 1} max={20000} unit="Hz" />
      <SliderElement label="Weighting" value={powering} onValueChange={setPowering} min={0} max={3} step={0.01} />
      <div className="my-3 border-t border-white/5" />
      <DataElement label="Frequencies" direction="output" shape={[freqBins]} unit="Hz" />
      <DataElement label="Data" direction="output" shape={[data?.length ?? freqBins]} />
      <BarChartElement data={data ?? preview} xMin={minFrequency} xMax={maxFrequency} preview={data === undefined} />
    </Node>
  );
}

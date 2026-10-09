from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class PitchClassChromaNode(CNode, AudioPipeline):
    """Fold spectral amplitudes into twelve pitch classes across octaves.

    Inputs `amplitudes` and `frequencies` are matching vectors (Hz).
    Output `data` has shape (12,), peak-normalized to [0, 1] each audio update;
    bin zero is the `reference_frequency` pitch (default A, 440 Hz), followed
    by semitones. Nonpositive frequencies are ignored; silence gives zeros."""

    nodeName = "PitchClassChroma"

    def __init__(
        self,
        amplitudes=np.zeros(FREQ_BINS),
        frequencies=np.zeros(FREQ_BINS),
        reference_frequency: int | float = 440.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "amplitudes": {"io": "in"},
            "frequencies": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.amplitudes = DataElement(self, 'amplitudes', ElementValue(amplitudes))
        self.frequencies = DataElement(self, 'frequencies', ElementValue(frequencies))
        self.reference_frequency = LinearDial(self, 'reference_frequency', 20, 2000, ElementValue(reference_frequency))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(12)))

    def c_update(self):
        amplitudes = np.maximum(np.asarray(self.amplitudes.value, dtype=float).reshape(-1), 0.0)
        frequencies = np.asarray(self.frequencies.value, dtype=float).reshape(-1)
        size = min(amplitudes.size, frequencies.size)
        self.data.value[:] = 0.0
        if size == 0:
            return

        amplitudes = amplitudes[:size]
        frequencies = frequencies[:size]
        valid = frequencies > 0
        if not np.any(valid):
            return

        pitch_classes = np.mod(
            np.round(12 * np.log2(frequencies[valid] / float(self.reference_frequency.value))).astype(int),
            12,
        )
        np.add.at(self.data.value, pitch_classes, amplitudes[valid])
        peak = np.max(self.data.value)
        if peak > 1e-12:
            self.data.value[:] = self.data.value / peak

from backend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from config import FREQ_BINS, MAX_FREQUENCY
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class SpectralCentroidNode(CNode, AudioPipeline):
    """Measure spectral brightness as an amplitude-weighted frequency.

    Inputs `amplitudes` and `frequencies` are matching spectrum vectors.
    Output `data` is a one-element array in Hz each audio update; negative
    amplitudes are ignored and silent or empty input gives zero."""

    nodeName = "SpectralCentroid"

    def __init__(
        self,
        amplitudes=np.zeros(FREQ_BINS),
        frequencies=np.zeros(FREQ_BINS),
        alias: str | None = None,
    ) -> None:
        terminals = {
            "amplitudes": {"io": "in"},
            "frequencies": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)
        self.amplitudes = DataElement(self, 'amplitudes', ElementValue(amplitudes))
        self.frequencies = DataElement(self, 'frequencies', ElementValue(frequencies))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))

    def c_update(self):
        amplitudes = np.maximum(np.asarray(self.amplitudes.value, dtype=float).reshape(-1), 0.0)
        frequencies = np.asarray(self.frequencies.value, dtype=float).reshape(-1)
        size = min(amplitudes.size, frequencies.size)
        if size == 0:
            self.data.value[...] = 0.0
            return
        amplitudes = amplitudes[:size]
        frequencies = frequencies[:size]
        self.data.value[...] = np.sum(frequencies * amplitudes) / (np.sum(amplitudes) + 1e-12)

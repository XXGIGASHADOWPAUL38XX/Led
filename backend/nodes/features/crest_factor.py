from backend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class CrestFactorNode(CNode, AudioPipeline):
    """Measure waveform peak relative to RMS for transient detection.

    Input `buffer_data` is audio, typically shaped (channels, samples).
    Output `data` is a one-element array of max(abs(audio)) / RMS over all
    channels and samples each audio update; empty or silent input gives zero."""

    nodeName = "CrestFactor"

    def __init__(self, buffer_data=np.zeros((2, 0)), alias: str | None = None) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)
        self.buffer_data = DataElement(self, 'buffer_data', ElementValue(buffer_data))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))

    def c_update(self):
        data = np.asarray(self.buffer_data.value, dtype=float)
        if data.size == 0:
            self.data.value[...] = 0.0
            return
        peak = np.max(np.abs(data))
        rms = np.sqrt(np.mean(data ** 2))
        self.data.value[...] = peak / (rms + 1e-12)

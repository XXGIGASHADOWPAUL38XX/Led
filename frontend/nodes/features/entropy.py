import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class EntropyNode(CNode, AudioPipeline):
    """Measure how evenly spectral amplitude is distributed.

    Input `amplitudes` is a spectrum vector. Output `data` is a one-element
    array of normalized spectral entropy, approximately [0, 1], each audio
    update. Negative amplitudes are ignored; silence gives zero."""

    nodeName = "Entropy"

    def __init__(self, amplitudes=np.zeros(FREQ_BINS), render: bool = True, alias: str | None = None) -> None:
        terminals = {
            "amplitudes": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.amplitudes = Element(self, "amplitudes", ElementValue(amplitudes))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))

    def c_update(self):
        amplitudes = np.maximum(np.asarray(self.amplitudes.value, dtype=float).reshape(-1), 0.0)
        total = np.sum(amplitudes)
        if amplitudes.size < 2 or total <= 1e-12:
            self.data.value[...] = 0.0
            return
        probabilities = amplitudes / total
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-12))
        self.data.value[...] = entropy / np.log2(amplitudes.size)

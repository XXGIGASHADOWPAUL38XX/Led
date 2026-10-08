import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class OnsetStrengthNode(CNode, AudioPipeline):
    """Detect spectral attacks above a moving noise floor.

    Input `amplitudes` is a spectrum vector. Output `data` is a nonnegative
    one-element array each audio update: mean positive change from the
    previous spectrum minus an exponential noise estimate. Keeps frame history."""

    nodeName = "OnsetStrength"

    def __init__(self, amplitudes=np.zeros(FREQ_BINS), render: bool = True, alias: str | None = None) -> None:
        terminals = {
            "amplitudes": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.amplitudes = Element(self, "amplitudes", ElementValue(amplitudes))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)), y_max=10.0)
        self.previous = np.zeros_like(np.asarray(self.amplitudes.value, dtype=float).reshape(-1))
        self.noise_floor = 0.0

    def c_update(self):
        amplitudes = np.asarray(self.amplitudes.value, dtype=float).reshape(-1)
        if amplitudes.size == 0:
            self.data.value[...] = 0.0
            return
        if self.previous.size != amplitudes.size:
            self.previous = np.zeros_like(amplitudes)
        rectified_flux = float(np.mean(np.maximum(amplitudes - self.previous, 0.0)))
        self.noise_floor = (self.noise_floor * 0.95) + (rectified_flux * 0.05)
        self.data.value[...] = max(rectified_flux - self.noise_floor, 0.0)
        self.previous[:] = amplitudes

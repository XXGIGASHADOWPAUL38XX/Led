import numpy as np
from scipy.signal import butter

from config import SAMPLE_RATE, FFT_SIZE
from frontend.components.elements.dials import LinearDial
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode
from frontend.nodes.pipelines.auditory.filter.filter import Filter


class HighFilterPipelineNode(CNode, Filter):
    """Apply a first-order Butterworth high-pass filter to audio.

    Input `buffer_data` and output `data` have shape (channels, samples).
    Configure `highpass_freq` in Hz, within (0, SAMPLE_RATE / 2).
    Each audio update filters along the sample axis at SAMPLE_RATE;
    filter state is reset for each block.
    """

    nodeName = "HighFilter"

    def __init__(
        self,
        buffer_data: np.ndarray = np.zeros((2, FFT_SIZE)),
        highpass_freq: float = 20.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.buffer_data = Element(self, "buffer_data", ElementValue(buffer_data))
        Filter.__init__(self, buffer_data=self.buffer_data)

        self.highpass_freq = LinearDial(self, "highpass_freq", 20, 5000, ElementValue(highpass_freq))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.buffer_data.value.shape)), y_min=-1.0)

    @staticmethod
    def butter_highpass(highcut, fs, order=1):
        nyq = 0.5 * fs
        high = highcut / nyq
        return butter(order, high, btype="highpass")

    def filter_coefficients(self, fs, order=1):
        return self.butter_highpass(self.highpass_freq.value, fs, order)

    def c_update(self):
        self.data.value[:] = self.apply_filter(self.buffer_data.value, SAMPLE_RATE)

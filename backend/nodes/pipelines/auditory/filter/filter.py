import numpy as np
from scipy.signal import hilbert, lfilter

from backend.updatable.updatable import AudioUpdatable
from config import SAMPLE_RATE
from backend.components.elements.element_value import ElementValue

class Filter(AudioUpdatable):
    def __init__(self, buffer_data: np.ndarray = np.zeros((2, 0))) -> None:
        super().__init__()
        self._buffer_data = ElementValue(buffer_data)

    def apply_filter(self, data, fs: int = SAMPLE_RATE, order: int = 1):
        b, a = self.filter_coefficients(fs, order)
        return lfilter(b, a, data)

    def filter_coefficients(self, fs: int, order: int = 1):
        raise NotImplementedError

    @staticmethod
    def envelope(signal):
        analytic_signal = hilbert(signal)
        return np.abs(analytic_signal)

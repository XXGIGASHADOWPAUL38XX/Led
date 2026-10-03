import numpy as np
from scipy.signal import get_window

from config import FFT_SIZE, FREQ_BINS, MAX_FREQUENCY, MIN_FREQUENCY, SAMPLE_RATE
from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements.dials import ExpDial, LinearDial
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class AmplitudesNode(CNode, AudioUpdatable):
    nodeName = "Amplitudes"

    def __init__(
            self,
            buffer: np.ndarray = np.zeros((2, FFT_SIZE)),
            min_frequency: int | float = MIN_FREQUENCY,
            max_frequency: int | float = MAX_FREQUENCY,
            fft_size: int = FFT_SIZE,
            freq_bins: int = FREQ_BINS,
            powering: int | float = 0.5,
            render: bool = True,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "buffer": {"io": "in"},
            "frequencies": {"io": "out"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.freq_bins = Element(self, "freq_bins", ElementValue(freq_bins))
        self.buffer = Element(self, "buffer", ElementValue(buffer))
        self.fft_size = Element(self, "fft_size", ElementValue(fft_size))
        self.window = get_window('hann', self.fft_size.value)
        self.min_frequency = ExpDial(self, "min_frequency", 20, 2000, ElementValue(min_frequency))
        self.max_frequency = Element(self, "max_frequency", ElementValue(max_frequency))
        self.frequencies = Element(
            self, "frequencies", ElementValue(np.geomspace(self.min_frequency.value, self.max_frequency.value, self.freq_bins.value))
        )
        self.powering = LinearDial(self, "powering", 0, 3, ElementValue(powering))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.freq_bins.value)), y_max=60.0)

    def c_update(self):
        self.buffer_to_amplitudes()

    def buffer_to_amplitudes(self):
        windowed = self.buffer.value * self.window
        fft_result = np.fft.rfft(windowed, n=self.fft_size.value)
        fft_frequencies = np.fft.rfftfreq(self.fft_size.value, d=1.0 / SAMPLE_RATE)
        fft_amplitudes = np.mean(np.abs(fft_result), axis=0)
        target_frequencies = self.frequencies.value
        updated_amplitudes = np.interp(
            target_frequencies,
            fft_frequencies,
            fft_amplitudes,
            left=0.0,
            right=0.0,
        )
        updated_amplitudes = updated_amplitudes * np.power(self.frequencies.value, self.powering.value)
        amplitude_ratio = updated_amplitudes / np.sum(self.window)
        updated_amplitudes = 20.0 * (np.log10(np.maximum(amplitude_ratio, 1e-12) + 1))

        self.data.value[:] = updated_amplitudes

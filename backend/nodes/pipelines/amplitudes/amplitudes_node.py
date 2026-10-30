from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from scipy.signal import get_window

from config import FFT_SIZE, FREQ_BINS, MAX_FREQUENCY, MIN_FREQUENCY, SAMPLE_RATE
from backend.updatable.updatable import AudioUpdatable

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class AmplitudesNode(CNode, AudioUpdatable):
    """Convert a stereo audio window to a logarithmically spaced spectrum.

    Input `buffer` has shape (2, fft_size), channels first. Outputs
    `frequencies` (Hz) and `data` have shape (freq_bins,). Each audio update
    applies a Hann window, averages channel FFT magnitudes, interpolates bins,
    weights by frequency ** powering, and applies 20 * log10(1 + amplitude).
    Configure `fft_size`, `freq_bins`, and frequency bounds; uses SAMPLE_RATE."""

    nodeName = "Amplitudes"

    def __init__(
            self,
            buffer: np.ndarray = np.zeros((2, FFT_SIZE)),
            min_frequency: int | float = MIN_FREQUENCY,
            max_frequency: int | float = MAX_FREQUENCY,
            fft_size: int = FFT_SIZE,
            freq_bins: int = FREQ_BINS,
            powering: int | float = 0.5,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "buffer": {"io": "in"},
            "frequencies": {"io": "out"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.freq_bins = Parameter(self, 'freq_bins', freq_bins, minimum=1, maximum=4096, integer=True)
        self.buffer = DataElement(self, 'buffer', ElementValue(buffer))
        self.fft_size = Parameter(self, 'fft_size', fft_size, minimum=16, maximum=65536, integer=True)
        self.window = get_window('hann', self.fft_size.value)
        self.min_frequency = Parameter(self, 'min_frequency', min_frequency, minimum=20, maximum=20000)
        self.max_frequency = Parameter(self, 'max_frequency', max_frequency, minimum=20, maximum=20000)
        self.frequencies = DataElement(self, 'frequencies', ElementValue(np.geomspace(self.min_frequency.value, self.max_frequency.value, self.freq_bins.value)))
        self.powering = Parameter(self, 'powering', powering, minimum=0, maximum=3)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.freq_bins.value)))

    def validate_parameters(self, changes):
        low = changes.get("min_frequency", self.min_frequency.value)
        high = changes.get("max_frequency", self.max_frequency.value)
        fft_size = changes.get("fft_size", self.fft_size.value)
        if not 0 < low < high <= SAMPLE_RATE / 2:
            raise ValueError("Frequency bounds must be ordered and below Nyquist")
        if self.buffer.value.ndim != 2 or self.buffer.value.shape[0] != 2:
            raise ValueError("Audio buffer must have two channels")
        if self.buffer._value_source is not None and self.buffer.value.shape[-1] != fft_size:
            raise ValueError("FFT size must match the connected audio buffer")

    def parameters_changed(self, name):
        self.window = get_window("hann", self.fft_size.value)
        if self.buffer._value_source is None and self.buffer.value.shape != (2, self.fft_size.value):
            self.buffer.value = np.zeros((2, self.fft_size.value))
        self.frequencies.value = np.geomspace(self.min_frequency.value, self.max_frequency.value, self.freq_bins.value)
        if self.data.value.shape != (self.freq_bins.value,):
            self.data.value = np.zeros(self.freq_bins.value)

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

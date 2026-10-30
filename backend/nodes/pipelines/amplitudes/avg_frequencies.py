from backend.components.elements.parameters import DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import FREQ_BINS, MAX_FREQUENCY
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class AvgFrequenciesNode(CNode, AudioUpdatable):
    """Compute the amplitude-weighted average frequency.

    Inputs `input_frequencies` (Hz) and `input_amplitudes` are matching vectors.
    Output `data` is a one-element array in Hz each audio update, using a
    small denominator epsilon so silent spectra produce zero."""

    nodeName = "AvgFrequencies"

    def __init__(
        self,
        input_frequencies: np.ndarray = np.zeros(FREQ_BINS),
        input_amplitudes: np.ndarray = np.zeros(FREQ_BINS),
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_frequencies": {"io": "in"},
            "input_amplitudes": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.input_frequencies = DataElement(self, 'input_frequencies', ElementValue(input_frequencies))
        self.input_amplitudes = DataElement(self, 'input_amplitudes', ElementValue(input_amplitudes))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))

    def c_update(self):
        self.data.value[...] = np.sum(
            (self.input_amplitudes.value * self.input_frequencies.value)
            / np.sum(self.input_amplitudes.value + 1e-12)
        )

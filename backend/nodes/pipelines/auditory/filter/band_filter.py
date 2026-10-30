from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from scipy.signal import butter

from config import SAMPLE_RATE, FFT_SIZE

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.nodes.pipelines.auditory.filter.filter import Filter

class BandFilterPipelineNode(CNode, Filter):
    """Apply a first-order Butterworth band-pass filter to audio.

    Input `buffer_data` and output `data` have shape (channels, samples).
    Configure `lowcut` and `highcut` in Hz, within (0, SAMPLE_RATE / 2).
    Each audio update filters along the sample axis at SAMPLE_RATE;
    filter state is reset for each block.
    """

    nodeName = "BandFilter"

    def __init__(
        self,
        buffer_data: np.ndarray = np.zeros((2, FFT_SIZE)),
        lowcut: float = 500.0,
        highcut: float = 3000.0,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)
        self.buffer_data = DataElement(self, 'buffer_data', ElementValue(buffer_data))
        Filter.__init__(self, buffer_data=self.buffer_data)

        self.lowcut = Parameter(self, 'lowcut', lowcut, minimum=20, maximum=1000)
        self.highcut = Parameter(self, 'highcut', highcut, minimum=100, maximum=10000)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.buffer_data.value.shape)))

    @staticmethod
    def butter_bandpass(lowcut, highcut, fs, order=1):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        return butter(order, [low, high], btype="band")

    def filter_coefficients(self, fs, order=1):
        return self.butter_bandpass(self.lowcut.value, self.highcut.value, fs, order)

    def c_update(self):
        self.data.value[:] = self.apply_filter(self.buffer_data.value, SAMPLE_RATE)

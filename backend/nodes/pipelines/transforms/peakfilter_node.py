from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class PeakFilterNode(CNode, AudioUpdatable):
    """Keep only the strongest local peaks in a vector.

    Input `input_value` produces same-shaped output `data` each audio update.
    Configure nonnegative `peaks_to_keep`; values below an adjacent sample
    and all but the largest remaining peaks become zero."""

    nodeName = "PeakFilter"

    def __init__(
        self,
        input_value: np.ndarray = np.zeros(0),
        peaks_to_keep: int = 20,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.input_value = DataElement(self, 'input_value', ElementValue(input_value))
        self.peaks_to_keep = Parameter(self, 'peaks_to_keep', peaks_to_keep, minimum=1, maximum=4096, integer=True)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_value.value)))

    def c_update(self):
        # Keep spikes
        values = np.asarray(self.input_value.value)
        if self.data.value.shape != values.shape:
            self.data.value = np.zeros_like(values)
        self.data.value[:] = values

        mask = np.zeros(values.shape, dtype=bool)
        mask[1:] |= values[1:] < values[:-1]
        mask[:-1] |= values[:-1] < values[1:]
        self.data.value[:] = self.input_value.value
        self.data.value[mask] = 0

        # Keep top n spikes
        values = self.data.value
        peak_count = min(int(self.peaks_to_keep.value), values.size)
        if peak_count == 0:
            self.data.value[:] = 0
            return

        keep = np.argsort(values)[-peak_count:]
        mask = np.ones(values.shape, dtype=bool)
        mask[keep] = False
        self.data.value[mask] = 0

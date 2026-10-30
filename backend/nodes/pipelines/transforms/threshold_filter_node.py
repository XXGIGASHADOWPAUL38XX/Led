from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class ThresholdFilterNode(CNode, AudioUpdatable):
    """Suppress array values below a threshold.

    Inputs `input_value` and scalar `threshold` produce same-shaped output
    `data` each audio update. Values below threshold become zero; values at
    or above threshold are retained."""

    nodeName = "ThresholdFilter"

    def __init__(
        self,
        input_value: np.ndarray = np.zeros(0),
        threshold: float = 0.0,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "threshold": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.input_value = DataElement(self, 'input_value', ElementValue(input_value))
        self.threshold = Parameter(self, 'threshold', threshold, minimum=-100, maximum=100)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_value.value)))

    def c_update(self):
        values = np.asarray(self.input_value.value)
        if self.data.value.shape != values.shape:
            self.data.value = np.zeros_like(values)

        self.data.value[:] = values
        self.data.value[values < float(self.threshold.value)] = 0

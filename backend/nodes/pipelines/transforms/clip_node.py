from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class ClipNode(CNode, AudioUpdatable):
    """Clamp an array to a fixed numeric range.

    Input `input_value` produces output `data` with the same shape each audio
    update. Configure `min_value` and `max_value`; values outside the range
    become the nearest bound."""

    nodeName = "Clip"

    def __init__(
        self,
        input_value: np.ndarray = np.zeros(0),
        min_value: float = 0.0,
        max_value: float = 1.0,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.input_value = DataElement(self, 'input_value', ElementValue(input_value))
        self.min_value = Parameter(self, 'min_value', min_value, minimum=-10000, maximum=10000)
        self.max_value = Parameter(self, 'max_value', max_value, minimum=-10000, maximum=10000)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_value.value)))

    def c_update(self):
        if self.data.value.shape != self.input_value.value.shape:
            self.data.value = np.zeros_like(self.input_value.value)
        self.data.value[:] = np.clip(
            self.input_value.value,
            float(self.min_value.value),
            float(self.max_value.value),
        )

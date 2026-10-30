from backend.components.elements.parameters import Parameter
import numpy as np

from config import FREQ_BINS
from backend.components.elements.analysable_element import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class ConstantArrayNode(CNode):
    """Generate a constant vector for masks, levels, or array arithmetic.

    Inputs `input_value` and `length` set the repeated value and element count.
    Output `data` has shape (length,) and refreshes when either input changes."""

    nodeName = "ConstantArray"

    def __init__(
        self,
        input_value: float = 0.0,
        length: int = FREQ_BINS,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "length": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)
        self.input_value = Parameter(self, 'input_value', input_value, minimum=-100, maximum=100)
        self.length = Parameter(self, 'length', length, minimum=1, maximum=4096, integer=True)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(int(self.length.value))))
        self.input_value.valueChanged.connect(self._refresh_data)
        self.length.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        self.data.value = np.repeat(self.input_value.value, int(self.length.value))

import numpy as np

from config import FREQ_BINS
from frontend.components.elements.analysable_element import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class ConstantArrayNode(CNode):
    """Generate a constant vector for masks, levels, or array arithmetic.

    Inputs `input_value` and `length` set the repeated value and element count.
    Output `data` has shape (length,) and refreshes when either input changes."""

    nodeName = "ConstantArray"

    def __init__(
        self,
        input_value: float = 0.0,
        length: int = FREQ_BINS,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "length": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.input_value = TextEdit(self, "input_value", ElementValue(input_value))
        self.length = Element(self, "length", ElementValue(length))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(int(self.length.value))), y_min=min(0.0, input_value), y_max=max(1.0, input_value))
        self.input_value.valueChanged.connect(self._refresh_data)
        self.length.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        self.data.value = np.repeat(self.input_value.value, int(self.length.value))

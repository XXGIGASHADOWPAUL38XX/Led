from frontend.components.elements.parameters import DataElement, IntegerDial, ReferenceElement
from backend.updatable.updatable import AudioUpdatable

import numpy as np

from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode
from frontend.nodes.window.window import WindowNode
from backend.windows_fcts.window_fct import WindowFct
from frontend.nodes.windows_fcts.averaged_window_fct import AveragedWindowFct


class SmoothingNode(CNode, AudioUpdatable):
    """Wrap a history window and aggregation function for signal smoothing.

    Input `input_value` is a vector; output `data` has its last-axis length.
    Configure positive history `length`, update delay `offset`, `avg_axis`
    (default 0), and optional `window_function` (default AveragedWindowFct).
    Child nodes retain history; c_update attempts to copy the aggregate and
    keeps the previous output if that copy fails."""

    nodeName = "Smoothing"

    def __init__(
            self,
            input_value: np.ndarray = np.zeros(0),
            length: int = 1,
            window_function: WindowFct | None = None,
            avg_axis: int | tuple[int, ...] | None = 0,
            offset: int = 0,
            render: bool = True,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_value = DataElement(self, 'input_value', ElementValue(input_value))

        self.length = IntegerDial(self, 'length', 1, 4096, ElementValue(length))
        self.window = ReferenceElement(self, 'window', WindowNode(input_data=self.input_value, length=self.length.value, offset=offset, render=False, parent=self))

        window_function = ReferenceElement(self, 'window_function', ElementValue(AveragedWindowFct(self.window.value, avg_axis=avg_axis, parent=self)) if not window_function else window_function)
        self.window_function = window_function
        self.average_window = window_function
        self.avg_axis = self.average_window.value.avg_axis
        self.offset = self.window.value.offset

        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.input_value.value.shape[-1])))
        self.length.valueChanged.connect(self._sync_length)

    def _sync_length(self, value):
        self.data.value = np.zeros(self.input_value.value.shape[-1])
        self.window.value.length.value = value

    def c_update(self):
        if not hasattr(self, "average_window"):
            return
        try:
            self.data.value[...] = self.average_window.value.data.value
        except Exception as e:
            pass

    # def connected(self, localTerm, remoteTerm):
    #     super().connected(localTerm, remoteTerm)

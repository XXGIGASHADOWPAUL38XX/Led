from frontend.components.elements.parameters import AxisElement
import numpy as np

from frontend.nodes.windows_fcts.window_fct import WindowFct
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class SumWindowFct(WindowFct, CNode):
    """Compute the sum of a WindowNode history.

    Configure `window` and `avg_axis` (0 for per-position history reduction;
    None reduces all axes). Output `data` receives the sum when
    the window calls `aggregate(window_data)` after each audio update.
    Connect Window.data to input `window`, or select it with the NodeSelector."""

    nodeName = "SumWindowFct"

    def __init__(
        self,
        window: CNode | None = None,
        avg_axis: int | tuple[int, ...] | None = None,
        render: bool = True,
        alias: str | None = None,
        parent: CNode | None = None,
    ) -> None:
        terminals = {"data": {"io": "out"}}
        CNode.__init__(self, self.nodeName, terminals=terminals, render=render, alias=alias, parent=parent)
        self.avg_axis = AxisElement(self, 'avg_axis', ElementValue(avg_axis))
        WindowFct.__init__(self, window, self.aggregate)
        if self._registered_window is not None:
            history = self._registered_window.data.value
            self.data.y_max.value = max(1.0, float(np.sum(np.ones(history.shape), axis=avg_axis).max(initial=0)))

    def _output_shape(self, history):
        return np.sum(np.zeros(history.shape), axis=self.avg_axis.value).shape or (1,)

    def aggregate(self, window_data):
        self.data.value[...] = np.sum(window_data, axis=self.avg_axis.value)

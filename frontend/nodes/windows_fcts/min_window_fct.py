from frontend.components.elements.parameters import AxisElement
import numpy as np

from frontend.nodes.windows_fcts.window_fct import WindowFct
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class MinWindowFct(WindowFct, CNode):
    """Compute the minimum of a WindowNode history.

    Configure `window` and `avg_axis` (0 for per-position history reduction;
    None reduces all axes). Output `data` receives the minimum when
    the window calls `aggregate(window_data)` after each audio update.
    Connect Window.data to input `window`, or select it with the NodeSelector."""

    nodeName = "MinWindowFct"

    def __init__(self, window: CNode | None = None, avg_axis=None, render: bool = True, alias: str | None = None, parent: CNode | None = None):
        CNode.__init__(self, self.nodeName, terminals={"data": {"io": "out"}}, render=render, alias=alias, parent=parent)
        WindowFct.__init__(self, window, self.aggregate)
        self.avg_axis = AxisElement(self, 'avg_axis', ElementValue(avg_axis))

    def aggregate(self, window_data):
        self.data.value[...] = np.min(window_data, axis=self.avg_axis.value)

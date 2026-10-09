from frontend.components.elements.parameters import AxisElement
import numpy as np

from frontend.nodes.windows_fcts.window_fct import WindowFct
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class CeilWindowFct(WindowFct, CNode):
    """Compute the ceiling of the maximum of a WindowNode history.

    Configure `window` and `avg_axis` (0 for per-position history reduction;
    None reduces all axes). Output `data` receives the ceiling of the maximum when
    the window calls `aggregate(window_data)` after each audio update.
    Connect Window.data to input `window`, or select it with the NodeSelector."""

    nodeName = "CeilWindowFct"

    def __init__(
        self,
        window: CNode | None = None,
        avg_axis: int | tuple[int, ...] | None = None,
        render: bool = True,
        alias: str | None = None,
        parent: CNode | None = None,
    ) -> None:
        terminals = {
            "data": {"io": "out"}
        }
        CNode.__init__(self, self.nodeName, terminals=terminals, render=render, alias=alias, parent=parent)
        WindowFct.__init__(self, window, self.aggregate)
        self.avg_axis = AxisElement(self, 'avg_axis', ElementValue(avg_axis))

    def aggregate(self, window_data):
        self.data.value[...] = np.ceil(np.max(window_data, axis=self.avg_axis.value))

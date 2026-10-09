from frontend.components.elements.parameters import AxisElement
import numpy as np

from frontend.nodes.windows_fcts.window_fct import WindowFct
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class AveragedWindowFct(WindowFct, CNode):
    """Compute the mean of a WindowNode history.

    Select or configure `window` and `avg_axis` (0 for per-position history reduction;
    None reduces all axes). Output `data` receives the mean when
    the window calls `aggregate(window_data)` after each audio update.
    Connect Window.data to input `window`, or select it with the NodeSelector."""

    nodeName = "AveragedWindowFct"

    def __init__(
        self,
        window: CNode | None = None,
        avg_axis: int | tuple[int, ...] | None = None,
        render: bool = True,
        parent: CNode | None = None,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "data": {"io": "out"}
        }
        CNode.__init__(self, self.nodeName, terminals=terminals, render=render, parent=parent, alias=alias)
        WindowFct.__init__(self, window, self.aggregate)
        self.avg_axis = AxisElement(self, 'avg_axis', ElementValue(avg_axis))

    def aggregate(self, window_data):
        self.data.value[...] = np.mean(window_data, axis=self.avg_axis.value)

from backend.components.elements.parameters import Parameter
import numpy as np

from backend.nodes.windows_fcts.window_fct import WindowFct
from backend.overrides.CNode import CNode

class MaxWindowFct(WindowFct, CNode):
    """Compute the maximum of a WindowNode history.

    Configure `window` and `avg_axis` (0 for per-position history reduction;
    None reduces all axes). Output `data` receives the maximum when
    the window calls `aggregate(window_data)` after each audio update.
    Connect Window.data to input `window`, or select it with the NodeSelector."""

    nodeName = "MaxWindowFct"

    def __init__(
        self,
        window: CNode | None = None,
        avg_axis: int | tuple[int, ...] | None = None,
        alias: str | None = None,
        parent: CNode | None = None,
    ) -> None:
        terminals = {
            "data": {"io": "out"}
        }
        CNode.__init__(self, self.nodeName, terminals=terminals, alias=alias, parent=parent)
        WindowFct.__init__(self, window, self.aggregate)
        self.avg_axis = Parameter(self, 'avg_axis', avg_axis, kind='axis')

    def aggregate(self, window_data):
        self.data.value[...] = np.max(window_data, axis=self.avg_axis.value)

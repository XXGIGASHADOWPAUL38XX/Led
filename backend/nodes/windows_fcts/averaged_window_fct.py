from backend.components.elements.parameters import Parameter
import numpy as np

from backend.nodes.windows_fcts.window_fct import WindowFct
from backend.overrides.CNode import CNode

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
        parent: CNode | None = None,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "data": {"io": "out"}
        }
        CNode.__init__(self, self.nodeName, terminals=terminals, parent=parent, alias=alias)
        WindowFct.__init__(self, window, self.aggregate)
        self.avg_axis = Parameter(self, 'avg_axis', avg_axis, kind='axis')

    def aggregate(self, window_data):
        self.data.value[...] = np.mean(window_data, axis=self.avg_axis.value)

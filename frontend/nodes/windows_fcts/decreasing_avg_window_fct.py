import numpy as np

from frontend.nodes.windows_fcts.window_fct import WindowFct
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class DecreasingAvgWindowFct(WindowFct, CNode):
    """Produce a decaying peak envelope from a WindowNode history.

    Select or configure `window` and `avg_axis` (usually 0). Output `data`
    is the maximum of history frames weighted linearly from oldest=0 to
    newest=1, not an average. The window calls aggregation each audio update;
    selection uses a NodeSelector rather than an input terminal."""

    nodeName = "DecreasingAvgWindowFct"

    def __init__(
        self,
        window: CNode | None = None,
        avg_axis: int | tuple[int, ...] | None = None,
        render: bool = True,
        alias: str | None = None,
        parent: CNode | None = None
    ) -> None:
        terminals = {
            "data": {"io": "out"}
        }
        CNode.__init__(self, self.nodeName, terminals=terminals, render=render, alias=alias, parent=parent)
        WindowFct.__init__(self, window, self.aggregate)
        self.avg_axis = Element(self, "avg_axis", ElementValue(avg_axis))

    def aggregate(self, window_data):
        if window_data.shape[0] <= 1:
            self.data.value[...] = np.max(window_data, axis=self.avg_axis.value)
            return

        weights = np.linspace(0.0, 1.0, window_data.shape[0])[:, None]
        self.data.value[...] = np.max(window_data * weights, axis=self.avg_axis.value)

import numpy as np

from backend.windows_fcts.window_fct import WindowFct
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class CeilWindowFct(WindowFct, CNode):
    nodeName = "CeilWindowFct"

    def __init__(
        self,
        window: CNode,
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
        self.window = window
        self.avg_axis = Element(self, "avg_axis", ElementValue(avg_axis))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(window.data.value.shape[-1])))

    def aggregate(self, window_data):
        self.data.value[...] = np.ceil(np.max(window_data, axis=self.avg_axis.value))

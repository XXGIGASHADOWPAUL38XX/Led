import numpy as np
from typing import Callable

from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.node_selector.node_selector import NodeSelector
from frontend.nodes.window.window import WindowNode
from frontend.overrides.CNode import CNode


class WindowFct:
    def __init__(
        self,
        window: WindowNode | None = None,
        aggregation: Callable[[np.ndarray], None] | None = None,
    ) -> None:
        self.aggregation = aggregation or self.aggregate
        self._registered_window = None
        self.window = NodeSelector(
            self,
            "window",
            ElementValue(window.window_fcts if window is not None else None),
            selection_nodes=self.get_flowchart_visible_nodes,
            link_terminal=False
        )
        self.data = AnalysableElement(self, "data",
                                      ElementValue(np.zeros(window.data.value.shape[-1] if window is not None else 1)))
        self.window.valueChanged.connect(self.on_window_change)
        self.on_window_change()

    def on_window_change(self):
        window = self.window.selected_node
        if window is None or not hasattr(window, "window_fcts"):
            return

        if self._registered_window is not window:
            if self._registered_window is not None and self in self._registered_window.window_fcts.value:
                self._registered_window.window_fcts.value.remove(self)
            window.window_fcts.value.append(self)
            self._registered_window = window

        data_shape = window.data.value.shape[-1]
        if self.data.value.shape != (data_shape,):
            self.data.value = np.zeros(data_shape)

    def aggregate(self, window_data):
        return

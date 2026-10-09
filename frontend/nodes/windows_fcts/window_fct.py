import numpy as np
from typing import Callable

from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.node_selector.node_selector import NodeSelector
from frontend.nodes.window.window import WindowNode


class WindowFct:
    def __init__(
        self,
        window: WindowNode | Element | None = None,
        aggregation: Callable[[np.ndarray], None] | None = None,
    ) -> None:
        self.aggregation = aggregation or self.aggregate
        self._registered_window = None
        self.pending_terminals["window"] = {"io": "in"}
        source = window.data if isinstance(window, WindowNode) else window
        self.window = NodeSelector(
            self, "window", ElementValue(source),
            selection_nodes=lambda: [node for node in self.get_flowchart_visible_nodes() if isinstance(node, WindowNode)],
            selection_elements=["data"],
        )
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))
        self.window.valueChanged.connect(self.on_window_change)
        self.on_window_change()

    def on_window_change(self):
        source = self.window._value_source
        window = source.node if source is not None and isinstance(source.node, WindowNode) and source is source.node.data else None
        if self._registered_window is not window:
            if self._registered_window is not None:
                self._registered_window.window_fcts.value.remove(self)
            self._registered_window = window
            if window is not None:
                window.window_fcts.value.append(self)
        if self.window.selected_element is not source:
            self.window.set_default_element(source)
        if window is not None:
            shape = self._output_shape(window.data.value)
            if self.data.value.shape != shape:
                self.data.value = np.zeros(shape)

    def _output_shape(self, history):
        return (history.shape[-1],)

    def close(self):
        if self._registered_window is not None:
            self._registered_window.window_fcts.value.remove(self)
            self._registered_window = None
        super().close()

    def aggregate(self, window_data):
        return

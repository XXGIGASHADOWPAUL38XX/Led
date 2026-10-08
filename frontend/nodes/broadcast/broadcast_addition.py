import numpy as np

from backend.pipelines.pipeline import VisualPipeline
from frontend.components.elements.dials import LinearDial
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class BroadcastAdditionNode(VisualPipeline, CNode):
    """Blend two arrays for mixing colors or visual signals.

    Inputs `input_data`, `secondary_data`, and `level` produce output `data`
    as input_data * (1 - level) + secondary_data * level each visual update.
    Shapes must broadcast; a per-position level expands over color channels."""

    nodeName = "BroadcastAddition"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(1),
        secondary_data: np.ndarray = np.zeros(1),
        level: np.ndarray = np.array(1.0),
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "secondary_data": {"io": "in"},
            "level": {"io": "in"},
            "data": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, render=render, alias=alias)

        self.input_data = Element(self, "input_data", ElementValue(input_data))
        self.secondary_data = Element(self, "secondary_data", ElementValue(secondary_data))
        level_value = level.value if isinstance(level, Element) else level
        if np.asarray(level_value).size > 1:
            self.level = Element(self, "level", ElementValue(level))
        else:
            self.level = LinearDial(self, "level", 0, 1, ElementValue(level))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_data.value)), y_max=255.0)

    def c_update(self):
        input_data = np.asarray(self.input_data.value)
        level = np.asarray(self.level.value)
        if level.shape != input_data.shape:
            while level.ndim < input_data.ndim:
                level = level[..., np.newaxis]
        data = input_data * (1 - level) + np.asarray(self.secondary_data.value) * level
        if self.data.value.shape != data.shape:
            self.data.value = np.zeros_like(data)
        self.data.value[:] = data

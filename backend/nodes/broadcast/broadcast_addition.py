from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.pipelines.pipeline import VisualPipeline

from backend.components.elements import AnalysableElement
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

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
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "secondary_data": {"io": "in"},
            "level": {"io": "in"},
            "data": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, alias=alias)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.secondary_data = DataElement(self, 'secondary_data', ElementValue(secondary_data))
        level_value = level.value if isinstance(level, Element) else level
        if np.asarray(level_value).size > 1:
            self.level = DataElement(self, 'level', ElementValue(level))
        else:
            self.level = Parameter(self, 'level', level, minimum=0, maximum=1)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_data.value)))

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

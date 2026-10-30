from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from config import FREQ_BINS
from backend.pipelines.pipeline import VisualPipeline
from backend.rainbow.config import ROLL_SPEED

from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class RollingNode(VisualPipeline, CNode):
    """Rotate a color or data array cyclically along its first axis.

    Input `input_data` initializes output `data` with the same array.
    Each visual update rolls the retained data by int(`roll_speed`) positions;
    this accumulates motion and writes into the shared source array."""

    nodeName = "RollingNode"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros((FREQ_BINS, 3)),
        roll_speed: int | float = ROLL_SPEED,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, alias=alias)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.roll_speed = Parameter(self, 'roll_speed', roll_speed, minimum=-10, maximum=10)
        self.data = DataElement(self, 'data', ElementValue(self.input_data.value))

    def c_update(self):
        self.data.value[:] = np.roll(self.data.value, int(self.roll_speed.value), axis=0)

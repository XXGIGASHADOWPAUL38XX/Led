from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from config import FREQ_BINS
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class BarGraphChartNode(CNode):
    """Expose bar heights and per-bar RGBA colors to frontend subscribers.

    Inputs `data` and `brushes` provide arrays; `number_points` records the
    light count. The node performs no rendering or signal transformation."""
    nodeName = 'BarGraphChart'

    def __init__(self, data: np.ndarray=np.zeros(FREQ_BINS), number_points: int=FREQ_BINS, brushes: np.ndarray | object=np.zeros((FREQ_BINS, 4)), alias: str | None=None) -> None:
        terminals = {'brushes': {'io': 'in'}, 'data': {'io': 'in'}}
        super().__init__(node_name=self.nodeName, terminals=terminals, alias=alias)
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.brushes = DataElement(self, 'brushes', ElementValue(brushes))
        self.data = DataElement(self, 'data', ElementValue(data))

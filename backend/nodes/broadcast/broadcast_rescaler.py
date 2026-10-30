from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import FREQ_BINS
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class BroadcastRescalerNode(CNode, AudioUpdatable):
    """Resize an array along its first axis by nearest lower-index sampling.

    Inputs `input_data` and positive `length` produce output `data` shaped
    (length, *input_data.shape[1:]) each audio update. Configure the output
    length at construction to match its allocated buffer."""

    nodeName = "BroadcastRescalerNode"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(FREQ_BINS),
        length: int = FREQ_BINS,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "length": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.length = Parameter(self, 'length', length, minimum=1, maximum=4096, integer=True)

        data_shape = (length, *self.input_data.value.shape[1:])
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(data_shape)))

    def c_update(self):
        ratio = self.input_data.value.shape[0] / self.length.value
        broadcast_indexes = np.floor(np.cumsum(np.repeat(ratio, self.length.value)) - ratio).astype(np.int16)
        self.data.value[:] = self.input_data.value[broadcast_indexes]

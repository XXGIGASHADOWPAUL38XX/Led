from backend.components.elements.parameters import Parameter, DataElement, NodeReferenceElement
import numpy as np

from config import FREQ_BINS
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.nodes.pipelines.amplitudes.amplitude_transformer import AmplitudesTransformer

class FctAmplitudesTransformerNode(CNode, AmplitudesTransformer):
    """Shape a spectrum with a supplied amplitude-level function.

    Input `input_data` is a FREQ_BINS vector; configure `amplitudes_level_fct`
    with an object exposing `fct(data)`. Output `data` applies that function
    then the constructor `log` exponent each audio update. The inherited
    transform mutates the function result; `powering` is currently unused."""

    nodeName = "FctAmplitudesTransformer"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(FREQ_BINS),
        powering: float = 1.,
        log: float = 1.,
        amplitudes_level_fct: object = None,

    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"},
        }
        CNode.__init__(self, self.nodeName, terminals, powering=powering, log=log)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.powering = Parameter(self, 'powering', powering, minimum=0, maximum=10)
        self.log = Parameter(self, 'log', log, minimum=0.01, maximum=10)
        self.log.valueChanged.connect(self._log_changed)
        self.amplitudes_level_fct = NodeReferenceElement(self, 'amplitudes_level_fct', amplitudes_level_fct)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(FREQ_BINS)))

    def c_update(self):
        if self.amplitudes_level_fct.value is None:
            return self.data
        self.transform_amplitudes(self.input_data.value)

    def validate_parameters(self, changes):
        function = self.amplitudes_level_fct.value
        if function is not None and function.data.value.shape != self.input_data.value.shape:
            raise ValueError("The amplitude function and input must have matching lengths")

    def transform_amplitudes(self, data):
        updated_amplitudes = data

        updated_amplitudes = self.amplitudes_level_fct.value.fct(updated_amplitudes)

        self.data.value[:] = super().transform_amplitudes(updated_amplitudes)

from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import DataElement, ReferenceElement
import numpy as np

from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode
from frontend.nodes.pipelines.amplitudes.amplitude_transformer import AmplitudesTransformer


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
        render: bool = True,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"},
        }
        CNode.__init__(self, self.nodeName, terminals, render=render)
        AmplitudesTransformer.__init__(self, powering=powering, log=log)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.powering = LinearDial(self, 'powering', 0, 10, ElementValue(powering))
        self.log = LinearDial(self, 'log', 0.01, 10, ElementValue(log))
        self.amplitudes_level_fct = ReferenceElement(self, 'amplitudes_level_fct', amplitudes_level_fct)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(FREQ_BINS)))

    def c_update(self):
        self.transform_amplitudes(self.input_data.value)

    def transform_amplitudes(self, data):
        updated_amplitudes = data

        updated_amplitudes = self.amplitudes_level_fct.value.fct(updated_amplitudes)

        self.data.value[:] = super().transform_amplitudes(updated_amplitudes)

import numpy as np

from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
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

        self.input_data = Element(self, "input_data", ElementValue(input_data))
        self.powering = Element(self, "powering", ElementValue(powering))
        self.log = Element(self, "log", ElementValue(log))
        self.amplitudes_level_fct = Element(self, "amplitudes_level_fct", amplitudes_level_fct)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(FREQ_BINS)))

    def c_update(self):
        self.transform_amplitudes(self.input_data.value)

    def transform_amplitudes(self, data):
        updated_amplitudes = data

        updated_amplitudes = self.amplitudes_level_fct.value.fct(updated_amplitudes)

        self.data.value[:] = super().transform_amplitudes(updated_amplitudes)

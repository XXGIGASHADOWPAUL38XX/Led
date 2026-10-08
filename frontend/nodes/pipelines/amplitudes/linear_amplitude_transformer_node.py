import numpy as np

from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode
from frontend.nodes.pipelines.amplitudes.amplitude_transformer import AmplitudesTransformer


class LinearAmplitudesTransformerNode(CNode, AmplitudesTransformer):
    """Apply optional triangular correlation and an exponent to a spectrum.

    Inputs `input_data`, `correlation_offset`, and `correlation_step` produce
    output `data` shaped (FREQ_BINS,) each audio update. Correlation runs only
    when both controls are supplied; step must be nonzero. The constructor
    `log` is an exponent; without correlation, the input is modified in place.
    `powering` is currently unused."""

    nodeName = "LinearAmplitudesTransformer"

    def __init__(
            self,
            input_data: np.ndarray = np.zeros(FREQ_BINS),
            correlation_offset: int | float | None = None,
            correlation_step: int | float | None = None,
            powering: float = 1.,
            log: float = 1.,
            render: bool = True,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "correlation_offset": {"io": "in"},
            "correlation_step": {"io": "in"},
            "data": {"io": "out"},
        }

        CNode.__init__(self, self.nodeName, terminals, render=render, alias=alias)
        AmplitudesTransformer.__init__(self, powering=powering, log=log)

        self.input_data = Element(self, "input_data", ElementValue(input_data))
        self.correlation_offset = Element(self, "correlation_offset", ElementValue(correlation_offset))
        self.correlation_step = Element(self, "correlation_step", ElementValue(correlation_step))
        self.powering = Element(self, "powering", ElementValue(powering))
        self.log = Element(self, "log", ElementValue(log))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(FREQ_BINS)))

    @staticmethod
    def _scalar(value):
        if value is None:
            return None
        return float(np.asarray(value).reshape(-1)[0])

    def c_update(self):
        self.transform_amplitudes(self.input_data.value)

    def transform_amplitudes(self, data):
        updated_amplitudes = data
        correlation_offset = self._scalar(self.correlation_offset.value)
        correlation_step = self._scalar(self.correlation_step.value)
        if correlation_offset is not None and correlation_step is not None:
            updated_amplitudes = np.correlate(
                updated_amplitudes,
                np.concatenate(
                    (
                        np.arange(1 - correlation_offset, 1, correlation_step),
                        np.arange(1, 1 - correlation_offset - correlation_step, -correlation_step)
                    )
                ),
                mode="same"
            )

        self.data.value[:] = super().transform_amplitudes(updated_amplitudes)
